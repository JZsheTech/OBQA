
• Updates

  - EviQAsys/backend/tests/manual/test_m4_qa_flow.py:36-200 now accepts --collection-id to reuse an existing index, defends against
    accidental --reset-db, skips ingestion when reusing, and prints clear reuse instructions (including the collection_id) whenever
    --keep is set so the saved resources can be referenced on the next run.
  - EviQAsys/backend/tests/manual/test_m4_multi_turn_qa_flow.py:1-204 is a new helper that shares the same ingestion/reuse workflow
    but enforces at least two --question flags, iterates turns on a single chat, and records the stored turn IDs so multi-turn QA
    behaviour can be inspected after the run.
  - Tests: not run (both scripts are manual validation tools and rely on live OceanBase/MinerU data).

  Next Steps

  1. Run the single-turn script once with --keep to ingest and persist a collection, note the printed collection_id, and reuse it on
     later executions via --collection-id <id> to skip re-indexing.
  2. Execute the multi-turn script with multiple --question arguments (and optionally --collection-id) to validate conversational
     behaviour across successive turns.

# Single Turn QA

单轮QA的结果：
(quest) shejunzhi@chai03:/data2/jproject/OBQA$ python EviQAsys/backend/tests/manual/test_m4_qa_flow.py --question "Please introduce the fine-tuning process of LLM."   --keep

===============================================================================
Running QA turn for question: Please introduce the fine-tuning process of LLM.

Assistant Answer:
The fine-tuning process of Large Language Models (LLMs) involves adjusting the model's parameters to
fit a specific task or dataset. This is typically done by adding a new layer on top of the pre-
trained model and training it on the target data [Elem#3502]. The goal of fine-tuning is to adapt
the model to perform well on a company's specific use case, rather than advancing the alignment of
general-purpose ML models [Elem#3633].  In the context of aligning language models with human
intentions, the fine-tuning data plays a crucial role in determining the end behavior of the model.
The fine-tuning process involves factors such as the underlying model, the training data, and the
alignment method used [Elem#3625]. For instance, when initializing RLHF models from a pre-trained
GPT-3 model, supervised fine-tuning is applied for 2 epochs on the demonstration dataset, with a mix
of 10% pretraining data during fine-tuning [Elem#3781].  The fine-tuning process can be influenced
by various factors, including the purpose of the efforts, the alignment method used, and the
characteristics of the training data. For example, when aligning to customer preferences, the
training data is determined by prompts sent by OpenAI customers to models on the OpenAI API
Playground [Elem#3629].  Overall, the fine-tuning process of LLMs involves a range of techniques and
considerations to adapt the model to specific tasks or datasets while ensuring alignment with human
intentions.

Evidences:
  - Evidence#1 element_id=3502 doc_id=11 page=8 type=text
      snippet: [3.5 models] [3.5 Models] We start with the GPT-3 pretrained language models from Brown et al. (2020). These models are trained on a broad distribution of Internet data and are adaptable to a wide ran...
  - Evidence#2 element_id=3633 doc_id=11 page=18 type=text
      snippet: [5.2 who are we aligning to?] [5.2 Who are we aligning to?] <sup>10</sup>Note that while fine-tuning models using human data is common practice when deploying ML systems, the purpose of these efforts ...
  - Evidence#3 element_id=3625 doc_id=11 page=18 type=text
      snippet: [5.2 who are we aligning to?] [5.2 Who are we aligning to?] When aligning language models with human intentions, their end behavior is a function of the underlying model (and its training data), the f...
  - Evidence#4 element_id=3781 doc_id=11 page=42 type=text
      snippet: [c.3 details of the initialization models for rlhf] [C.3 Details of the initialization models for RLHF] We initialize the RLHF models from a pretrained GPT-3 model and apply supervised fine-tuning for...
  - Evidence#5 element_id=3629 doc_id=11 page=18 type=text
      snippet: [5.2 who are we aligning to?] [5.2 Who are we aligning to?] Third, our training data is determined by prompts sent by OpenAI customers to models on the OpenAI API Playground, and thus we are implicitl...
================================================================================
Turn stored with id=3
Keep flag enabled; collection_id=6 remains available. Re-run with --collection-id 6 to reuse the indexed documents.

# multiTurn-QA Test

est) shejunzhi@chai03:/data2/jproject/OBQA$ clear
(quest) shejunzhi@chai03:/data2/jproject/OBQA$ python EviQAsys/backend/tests/manual/test_m4_multi_turn_qa_flow.py --question "What are the three core steps involved in a method for training language models to follow instructions?" --question "Regarding the step in the above method that requires training a separate reward model and optimizing through reinforcement learning, an improved approach proposes directly optimizing the language model using preference data. What is the main advantage claimed by this improved method?"      --keep    --collection-id 6
[2025-11-19 12:24:43.514922] Target DB: obqa_dev @ 127.0.0.1:2881
Reusing collection id=6 name=manual-m4-qa-flow; skipping ingestion.
Skipping ingestion and embedding; existing collection will be used.
Chat created id=5 for collection 6
================================================================================
Running QA turn #1 for question: What are the three core steps involved in a method for training language models to follow instructions?

Assistant Answer:
The three core steps involved in a method for training language models to follow instructions are
not explicitly stated in the provided evidence context. However, based on the available textual
evidences, we can infer that the steps might involve training models with different techniques
[Elem#3502], collecting and filtering data [Elem#3447], and iterating through comparison data to
train new policies [Elem#3481].

Evidences:
  - Evidence#1 element_id=3502 doc_id=11 page=8 type=text
      snippet: [3.5 models] [3.5 Models] We start with the GPT-3 pretrained language models from Brown et al. (2020). These models are trained on a broad distribution of Internet data and are adaptable to a wide ran...
  - Evidence#2 element_id=3447 doc_id=11 page=2 type=text
      snippet: [1 introduction] [1 Introduction] ${}^{3}$  Specifically,we train on prompts submitted to earlier versions of the InstructGPT models on the OpenAI API Playground, which were trained only using demonst...
  - Evidence#3 element_id=3481 doc_id=11 page=6 type=text
      snippet: [3.1 high-level methodology] [3.1 High-level methodology] Steps 2 and 3 can be iterated continuously; more comparison data is collected on the current best policy, which is used to train a new RM and ...
================================================================================
Turn #1 stored with id=5
================================================================================
Running QA turn #2 for question: Regarding the step in the above method that requires training a separate reward model and optimizing through reinforcement learning, an improved approach proposes directly optimizing the language model using preference data. What is the main advantage claimed by this improved method?

Assistant Answer:
The main advantage claimed by this improved method is that it directly optimizes the language model
using preference data, eliminating the need to train a separate reward model and optimize through
reinforcement learning. This approach simplifies the process and makes it more stable [Elem#4101].

Evidences:
  - Evidence#4 element_id=4101 doc_id=12 page=1 type=text
      snippet: [abstract] [Abstract] While large-scale unsupervised language models (LMs) learn broad world knowledge and some reasoning skills, achieving precise control of their behavior is difficult due to the co...
================================================================================
Turn #2 stored with id=6
Keep flag enabled; collection_id=6 remains available. Re-run with --collection-id 6 to reuse the indexed documents.
Stored turn ids: 5, 6



