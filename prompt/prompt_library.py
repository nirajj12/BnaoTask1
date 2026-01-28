from enum import Enum


class PromptType(str, Enum):
    CONTEXTUALIZE_QUESTION = "contextualize_question"
    CONTEXT_QA = "context_qa"


# ---------- Prompt for contextual question rewriting ----------

CONTEXTUALIZE_QUESTION_PROMPT = """
You are given a conversation history and a user query.

Rewrite the user query as a standalone question that can be understood
without the conversation history.

Rules:
- Do NOT answer the question.
- Only rewrite if necessary.
- If rewriting is not needed, return the original question.

Conversation History:
{chat_history}

User Question:
{question}

Standalone Question:
""".strip()


# ---------- Prompt for context-based question answering ----------

CONTEXT_QA_PROMPT = """
You are an assistant that answers questions strictly using the provided context.

Rules:
- Use ONLY the information in the context.
- If the answer is not present, say: "I don't know."
- Keep the answer concise (maximum 3 sentences).

Context:
{context}

Question:
{question}

Answer:
""".strip()


# ---------- Central Prompt Registry ----------

PROMPT_REGISTRY = {
    PromptType.CONTEXTUALIZE_QUESTION.value: CONTEXTUALIZE_QUESTION_PROMPT,
    PromptType.CONTEXT_QA.value: CONTEXT_QA_PROMPT,
}
