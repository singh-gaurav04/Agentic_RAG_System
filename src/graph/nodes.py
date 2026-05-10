import json

from rich import print

from langchain_mistralai import ChatMistralAI

from src.config.settings import Settings
from src.graph.state import AgentState
from src.retrieval.hybrid_retriever import HybridRetriever
from src.schemas.agent_schema import AgentAction, PlannerDecision, Reference, RetrievedDocument
from src.tools.web_search_tool import WebSearchTool
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages

class ModelNotAvailableError(Exception):
    pass


def _parse_planner_decision(state: AgentState) -> PlannerDecision | None:
    raw = state.get("planner_decision")
    if raw is None:
        return None
    return PlannerDecision.model_validate(raw)


def _parse_retrieved_documents(state: AgentState) -> list[RetrievedDocument]:
    return [RetrievedDocument.model_validate(d) for d in state["retrieved_docs"]]


class GraphNodes:
    def __init__(self, settings: Settings, retriever: HybridRetriever, web_search_tool: WebSearchTool) -> None:
        self.settings = settings
        self.retriever = retriever
        self.web_search_tool = web_search_tool
        self.llm = self.build_llm()
        self.planner_llm = self.llm.with_structured_output(PlannerDecision)

    def build_llm(self) -> ChatMistralAI:
        try:
            model: ChatMistralAI = ChatMistralAI(
                model=self.settings.mistral_model,
                api_key=self.settings.mistral_api_key,
                temperature=0.2,
                max_tokens=1000,
                streaming=True,
            )
            return model
        except Exception as e:
            raise ModelNotAvailableError(f"Failed to initialize Mistral AI model: {e}") from e

    async def planner_node(self, state: AgentState) -> AgentState:
        print("from planner node")
        system_prompt: str = ('''
          You are an AI agent responsible for managing user queries related to artificial intelligence and computer science research. Your task is to select the most appropriate action based on the user's message and message history, following these rules:

- Actions: answer, retrieve_documents, ask_clarification, web_search, refuse, rewrite_query, rerank_results.
- If the query is outside AI/CS research, choose **refuse** and set:
  <refusal_reason>I cannot answer outside the domain. I only answer AI-related questions.</refusal_reason>
- If the user message contains an AI-related link, choose **web_search**.
- Never refuse solely because the corpus may lack an answer; rely on retrieval or web search.
- Use **ask_clarification** only for ambiguous but AI-related queries.
- Use **answer** only for small-talk, meta-questions about the assistant, or messages that require no tools.
- Use **rewrite_query** only when rewriting improves retrieval.
- Use **retrieve_documents** for clear AI-related questions that should be grounded in indexed papers.
- Use **web_search** sparingly, mainly when retrieval is inappropriate (e.g., current events).
- Set the confidence score between 0 and 1 based on the certainty of your action.

Populate the following output fields:
- `rationale`: a brief explanation justifying your action
- `rewritten_query`: only if action is rewrite_query
- `clarification_question`: only if action is ask_clarification
- `refusal_reason`: only if action is refuse 
        '''
f"session_title: a concise, relevant title based on the user query and message history give single title for every session based on the session_id {state['session_id']}\n"
f"User message: {state['user_query']}\n"
f"Message history: {state['messages']}\n"
        )
        planner_output: PlannerDecision = await self.planner_llm.ainvoke(system_prompt)
        state["planner_decision"] = planner_output.model_dump(mode="json")
        state["rewritten_query"] = planner_output.rewritten_query or state["user_query"]
        state["confidence_signals"]["planner_confidence"] = planner_output.confidence
        state["traces"].append(
            {
                "node": "planner",
                "decision": state["planner_decision"],
            }
        )
        state["session_title"] = planner_output.session_title
        print("exiting planner node")
        return state

    async def retrieval_node(self, state: AgentState) -> AgentState:
        print("from retrieval node")
        query = state["rewritten_query"] or state["user_query"]
        retrieved_docs = await self.retriever.retrieve(query)
        retrieval_confidence: float = max((document.final_score for document in retrieved_docs), default=0.0)
        if retrieval_confidence < self.settings.min_retrieval_score:
            retrieved_docs = []
        state["retrieved_docs"] = [d.model_dump(mode="json") for d in retrieved_docs]
        state["confidence_signals"]["retrieval_confidence"] = retrieval_confidence
        state["traces"].append(
            {
                "node": "retrieval",
                "query": query,
                "retrieved_count": len(retrieved_docs),
                "scores": [document.final_score for document in retrieved_docs],
                "corpus_miss_fallback_web_search": len(retrieved_docs) == 0,
            }
        )
        print("exiting retrieval node")
        return state

    async def reranker_node(self, state: AgentState) -> AgentState:
        print("from reranker node")
        documents = sorted(_parse_retrieved_documents(state), key=lambda item: item.final_score, reverse=True)
        state["retrieved_docs"] = [d.model_dump(mode="json") for d in documents]
        state["traces"].append({"node": "reranker", "documents": [doc.id for doc in documents]})
        print("exiting reranker node")
        return state

    async def tool_node(self, state: AgentState) -> AgentState:
        print("from tool node")
        query: str = state["rewritten_query"] or state["user_query"]
        results = await self.web_search_tool.search(query, max_results=5)
        state["tool_outputs"] = [{"tool": "web_search", "results": results}]
        pd = state["planner_decision"]
        action = pd.get("action") if isinstance(pd, dict) else None
        state["traces"].append(
            {
                "node": "tool",
                "tool": "web_search",
                "results_count": len(results),
                "reason": "planner_choice" if action == AgentAction.web_search.value else "corpus_miss",
            }
        )
        print("exiting tool node")
        return state

    async def refusal_or_clarification_node(self, state: AgentState) -> AgentState:
        print("from refusal or clarification node")
        decision = _parse_planner_decision(state)
        if decision is None:
            state["final_answer"] = "i cannot answer or continue because no action was chosen by the planner."
            return state
        if decision.action == AgentAction.ask_clarification.value:
            state["final_answer"] = decision.clarification_question or "could you please provide more clarification?"
            return state
        if decision.action == AgentAction.refuse.value:
            state["final_answer"] = decision.refusal_reason or (
                "I cannot answer outside the domain. I only answer AI-related questions.\n\n"
                "If your question **is AI-related**, rephrase it and I’ll help."
            )
            return state
        state["final_answer"] = decision.refusal_reason or (
            "I don’t have enough information to answer that yet.\n\n"
            "**Next step:** rephrase your question or add details."
        )
        return state

    async def answer_node(self, state: AgentState) -> AgentState:
        documents = _parse_retrieved_documents(state)
        context: str = "\n\n".join(
            [
                f"[{index + 1}] {document.metadata.title} ({document.metadata.source_url})\n{document.content}"
                for index, document in enumerate(documents)
            ]
        )
        tool_context: str = json.dumps(state["tool_outputs"], ensure_ascii=True)
        pd = state["planner_decision"]
        planner_action = pd.get("action", "unknown") if isinstance(pd, dict) else "unknown"
        prompt: str = (
            '''You are a professional, agentic RAG assistant specialized in answering AI-related questions. Generate your responses in polished GitHub-Flavored Markdown, adhering to the following formatting rules:

- Begin with a brief introductory line, followed by ## subheadings for distinct sections.
- Use bullet or numbered lists for multiple points.
- Enclose code samples within fenced code blocks with appropriate language tags (e.g., python, bash, typescript).
- Highlight key phrases sparingly using bold (**term**).
- Cite grounded sources as Markdown links [title](url).

Grounding guidelines:
- Prioritize retrieved corpus excerpts when relevant.
- When corpus is sparse but Tool (web_search) JSON contains useful hits, faithfully summarize those.
- Clearly state if neither source provides sufficient information.
- Do not invent citations or URLs.



Ensure the response remains concise, professional, and resistant to hallucinations, with high-quality markdown rendering and grounded answers.
Input context:\n'''
f"User question: {state['user_query']}\n"
f"Planner action: {planner_action}\n"
f"Retrieved context: {context or '(none)'}\n"
f"Tool context: {tool_context}\n"
f"Message history: {state['messages']}\n"
        )
        result = await self.llm.ainvoke(prompt)
        answer_text: str = result.content if isinstance(result.content, str) else str(result.content)
        state["final_answer"] = answer_text
        state["references"] = [
            Reference(
                paper_id=document.metadata.paper_id,
                title=document.metadata.title,
                source_url=document.metadata.source_url,
                section=document.metadata.section,
            ).model_dump(mode="json")
            for document in documents
        ]
        state["traces"].append(
            {
                "node": "answer",
                "references_count": len(state["references"]),
            }
        )
        state["messages"] = add_messages(state["messages"], AIMessage(content=answer_text))
        print("exiting answer node")
        return state

    async def evaluation_hook_node(self, state: AgentState) -> AgentState:
        print("from evaluation hook node")
        state["traces"].append(
            {
                "node": "evaluation_hook",
                "planner_confidence": state["confidence_signals"].get("planner_confidence", 0.0),
                "retrieval_confidence": state["confidence_signals"].get("retrieval_confidence", 0.0),
            }
        )
        print("exiting evaluation hook node")
        return state
