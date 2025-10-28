# Background

Most general-purpose web-based AI tools, when asked to answer questions based on one or more PDF research papers, tend to read through the entire text and directly provide an answer. However, due to the inherent hallucination problem of large language models (LLMs), the generated answers may contain inaccuracies. Moreover, these web-based AI models usually do not show which parts of the original paper they relied on as *evidence*. This makes it difficult for users to judge whether the answer truly follows the source text, thereby reducing the reliability of AI-assisted academic reading.

# Requirement Analysis

We aim to design a **demo system** of a paper question-answering agent that explicitly displays *evidence*. The system should use several simple agents to let the AI, while answering a user’s question, also output the corresponding *evidence* — that is, specific *elements* (chunks) from the original document such as text paragraphs, figures, and tables. These evidence elements should be visually highlighted on the frontend.

The question-answering capability only needs to achieve the following basic functions:

* **Single-turn QA**:
  `{Multiple papers + single-hop question + one retrieval → Answer + evidence_element}`

* **Multi-turn QA**:
  Multiple single-turn QAs. Memory is simply built by concatenating the results of the most recent turns, with a maximum length limit — older turns are truncated when the limit is exceeded.

Frontend requirements:

* Users can create a **Collection**
* Users can **upload multiple papers** into a Collection
* Users can **ask questions** about all papers in a Collection
* The system maintains a **history** of user questions and answers.

To simplify the implementation (for teaching/demo purposes), we apply the following simplifications:

* Directly build the index using the elements parsed by **MinerU** (with only basic title-level filtering); no further re-segmentation or merging is performed.
* Directly use **dspy**’s built-in modules to wrap the LLM API for simple QA interactions, leveraging dspy’s *ReAct* mechanism so that the LLM can autonomously decide which modalities of evidence to retrieve.
* Each chat session uses only the most recent few turns as memory; when the memory exceeds the limit, a brief **summary** is used instead.

