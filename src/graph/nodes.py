from pydantic import BaseModel,Field
import json


from src.schemas.agent_schema import AgentAction
from src.config.settings import Settings
from src.retrieval.hybrid_retriever import HybridRetriever
from src.tools.web_search_tool import WebSearchTool
from src.graph.state import AgentState
from src.schemas.agent_schema import PlannerDecision
from src.schemas.agent_schema import RetrievedDocument
from src.schemas.agent_schema import Reference

from langchain_mistralai import ChatMistralAI

class ModelNotAvailableError(Exception):
    pass

class PlannerOutput(BaseModel):
    action: AgentAction
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    rewritten_query: str | None = None
    clarification_question: str | None = None
    refusal_reason: str | None = None

class GraphNodes:
    def __init__(self,settings:Settings,retriever:HybridRetriever,web_search_tool:WebSearchTool) -> None:

        self.settings = settings
        self.retriever = retriever
        self.web_search_tool = web_search_tool
        self.llm = self.build_llm()
        self.planner_llm = self.llm.with_structured_output(PlannerOutput)






        def build_llm(self)->ChatMistralAI:
            try:
                model = ChatMistralAI(
                    model = self.settings.mistral_model,
                    api_key = self.settings.mistral_api_key,
                    temperature = 0.2,
                    max_tokens= 1000,
                )
                return model
            except Exception as e:
                raise ModelNotAvailableError(f"Failed to initialize Mistral AI model: {e}")

        async def planner_node(self,state:AgentState)->PlannerOutput:

            SYSTEM_PROMPT :str = (
                "You are a planner for an agentic RAG system over recent cs.AI papers. "
                "Choose one action among retrieve_documents, ask_clarification, web_search, answer, refuse, rewrite_query, rerank_results.\n"
                f"Memory summary: {state['memory_summary']}\n"
                f"Conversation messages: {[message.model_dump() for message in state['conversation_history']]}\n"
                f"Current user message: {state['user_message']}\n"
                "Refuse if user asks outside domain or asks unsupported high-risk claim. "
                "Ask clarification if query is ambiguous."
                "Provide rationale for your choice and confidence score between 0 and 1."
            )

            planner_output : PlannerOutput = await self.planner_llm.ainvoke(SYSTEM_PROMPT) #asynchronous invoke

            state['planner_decision'] = PlannerDecision.model_validate(planner_output.model_dump())
            state["rewritten_query"] = planner_output.rewritten_query or state['user_query']
            state["confidence_signals"]["planner_confidence"] = planner_output.confidence
            state["traces"].append({
                "node": "planner",
                "decision": state['planner_decision'].model_dump(),
            })

            return state

        async def retrieval_node(self,state:AgentState)->list[RetrievedDocument]:

            query = state['rewritten_query'] or state['user_query']
            retrieved_docs = await self.retriever.retrieve(query)

            retrieval_confidence: float = max([document.final_score for document in retrieved_docs], default=0.0)
            
            if retrieval_confidence < self.settings.min_retrieval_score:
                retrieved_docs = []

            state['retrieved_docs'] = retrieved_docs
            state['confidence_signals']['retrieval_confidence'] = retrieval_confidence
            state['traces'].append({
                "node": "retrieval",
                 "query": query,
                 "retrieved_count": len(retrieved_docs),
                 "scores": [document.final_score for document in retrieved_docs],
            })

            return state


    async def reranker_node(self, state: AgentState) -> AgentState:
        documents = sorted(state["retrieved_docs"], key=lambda item: item.final_score, reverse=True)
        state["retrieved_docs"] = documents
        state["traces"].append({"node": "reranker", "documents": [doc.id for doc in documents]})
        return state
            
            
    async def tool_node(self, state: AgentState) -> AgentState:
         query: str = state["rewritten_query"] or state["user_message"]
         results = await self.web_search_tool.search(query,max_results=5)

         state["tool_outputs"] = [{"tool": "web_search", "results": results}]
         state["traces"].append({"node": "tool", "tool": "web_search", "results_count": len(results)})

         return state

    async def refusal_or_clarification_node(self, state: AgentState) -> AgentState:

        decision = state["planner_decision"]

        if decision is None:
            state["final_answer"] = "i cannot answer or continue because no action was chosen by the planner."
            return state

        if decision.action == AgentAction.ask_clarification:
            state["final_answer"] = decision.clarification_question or "could you please provide more clarification?"
            return state

        else:
            state["final_answer"] = "i need to refuse because i don't have the information to answer that question."
            return state
        


    async def answer_node(self, state: AgentState) -> AgentState:

        context: str = "\n\n".join(
            [
                f"[{index + 1}] {document.metadata.title} ({document.metadata.source_url})\n{document.content}"
                for index, document in enumerate(state["retrieved_docs"])
            ]
        )
        tool_context: str = json.dumps(state["tool_outputs"], ensure_ascii=True)

        print(f"from answer node context: {context}")
        print(f"from answer node tool context: {tool_context}")

        PROMPT: str = (
            "Answer only from provided evidence. If evidence is weak, explicitly say uncertainty.\n"
            f"User question: {state['user_message']}\n"
            f"Memory summary: {state['memory_summary']}\n"
            f"Retrieved context:\n{context}\n"
            f"Tool context:\n{tool_context}\n"
            "Provide concise factual answer with references."
        )

        result = await self.llm.ainvoke(PROMPT)
        answer_text: str = result.content if isinstance(result.content, str) else str(result.content)

        state["final_answer"] = answer_text
        state["references"] =[
            Reference(
                paper_id=document.metadata.paper_id,
                title=document.metadata.title,
                source_url=document.metadata.source_url,
                section=document.metadata.section,
            )
            for document in state["retrieved_docs"]
        ]
        state["traces"].append({
            "node": "answer",
            'referemces_count': len(state["references"]),
        })
        return state
        

    async def evaluation_hook_node(self, state: AgentState) -> AgentState:
        state["traces"].append(
            {
                "node": "evaluation_hook",
                "planner_confidence": state["confidence_signals"].get("planner_confidence", 0.0),
                "retrieval_confidence": state["confidence_signals"].get("retrieval_confidence", 0.0),
            }
        )
        return state


