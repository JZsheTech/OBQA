经过实验验证，我发现当前系统对于chunk合并的策略并不合适，在合并的element不能跨section的前提下，为了使得系统中合并后的各个Chunk大小更加平均，从而提高检索精度，我认为需要将当前索引建立的document_ingest相关方法改成下面的逻辑：
全部按照`CHARACTOR_CHUNK_SIZE` 来控制合并的大小，并且仍然禁止使用`OVERLAP` ：
设置 `MIN_CHARACTOR_CHUNK_SIZE`  `MAX_CHARACTOR_CHUNK_SIZE` ，然后对Chunk的构造逻辑调整如下：
- chunk_type现在仍分为text、table和image类型
- type为image的element具有独立性，只能单独成块，不能参与合并，embedding时需要将其caption与图片base64做联合嵌入。并且在chunk顺序上需要被放到section的末尾。
- type为table的element具有独立性, 只能单独成块，不能参与合并，embedding时需要将其text_content + caption(文本部分)与图片base64做联合嵌入。并且在chunk顺序上需要被放到section的末尾。
- type不为image/table的其他element都可以参与合并成为chunk(比如text, equation, header)，合并的是它们的raw_text_content，即文本部分。
- element合并成chunk时，可以跨越image/table类型的元素，即将image/table从合并列表中单独拎出去，两侧的其他类型的元素可以自由合并。
- `MAX_CHARACTOR_CHUNK_SIZE` > `MIN_CHARACTOR_CHUNK_SIZE`
- 合并策略：优先保证不跨section，其次保证 `MIN_CHARACTOR_CHUNK_SIZE` ，最后保证`MAX_CHARACTOR_CHUNK_SIZE`
	- no.1: element合并成chunk时，不能跨越section的边界(即具有不同level_nav的element不能合并)
	- no.2: element合并时，只能以element为单位进行逐个合并，从头向后扫描，顺序合并；
	- no.3: 如果单个element字符数超过`MAX_CHARACTOR_CHUNK_SIZE` ，让它单独成1个Chunk，不要去切分它
	- no.4: 从头向后顺序扫描并逐个合入Element，当字符数首次超过`MAX_CHARACTOR_CHUNK_SIZE` 时，如果最后一个Element合入前字符数超过`MIN_CHARACTOR_CHUNK_SIZE` ，就取合入最后一个Element之前的Chunk作为合并的Chunk，然后指针指向下一个element，否则取当前这个超过`MAX_CHARACTOR_CHUNK_SIZE` 的Chunk作为合并的Chunk 。

