# File Contract Summary: `emergency_restore/python/zstandard/backend_cffi.py`
- **Lines**: 4478
- **Symbols Count**: 201
- **Imports Count**: 6

### Key Dependencies (Imports)
`__future__`, `__future__`, `io`, `os`, `_cffi`, `_cffi`

### Exported / Defined Symbols
| Type | Name | Scope / Parent | Lines | Details |
| :--- | :--- | :--- | :--- | :--- |
| `function` | **`_cpu_count`** | `global` | L158-L172 |  |
| `class` | **`BufferSegment`** | `global` | L175-L195 | /* Represents a segment within a ``BufferWi */ |
| `method` | **`offset`** | `BufferSegment` | L185-L187 | args: (self) /* The byte offset of this segment within i */ |
| `function` | **`__len__`** | `BufferSegment` | L189-L191 | args: (self) /* Obtain the length of the segment, in byt */ |
| `function` | **`tobytes`** | `BufferSegment` | L193-L195 | args: (self) /* Obtain bytes copy of this segment. */ |
| `class` | **`BufferSegments`** | `global` | L198-L206 | /* Represents an array of ``(offset, length */ |
| `class` | **`BufferWithSegments`** | `global` | L209-L260 | /* A memory buffer containing N discrete it */ |
| `method` | **`size`** | `BufferWithSegments` | L231-L233 | args: (self) /* Total sizein bytes of the backing buffer */ |
| `function` | **`__len__`** | `BufferWithSegments` | L235-L236 | args: (self) |
| `function` | **`__getitem__`** | `BufferWithSegments` | L238-L248 | args: (self, i) /* Obtains a segment within the buffer. */ |
| `function` | **`segments`** | `BufferWithSegments` | L250-L256 | args: (self) /* Obtain the array of ``(offset, length)`` */ |
| `function` | **`tobytes`** | `BufferWithSegments` | L258-L260 | args: (self) /* Obtain bytes copy of this instance. */ |
| `class` | **`BufferWithSegmentsCollection`** | `global` | L263-L282 | /* A virtual spanning view over multiple Bu */ |
| `method` | **`__len__`** | `BufferWithSegmentsCollection` | L276-L278 | args: (self) /* The number of segments within all ``Buff */ |
| `function` | **`__getitem__`** | `BufferWithSegmentsCollection` | L280-L282 | args: (self, i) /* Obtain the ``BufferSegment`` at an offse */ |
| `class` | **`ZstdError`** | `global` | L285-L286 | extends: Exception |
| `function` | **`_zstd_error`** | `global` | L289-L293 | args: (zresult) |
| `function` | **`_make_cctx_params`** | `global` | L296-L330 | args: (params) |
| `class` | **`ZstdCompressionParameters`** | `global` | L333-L589 | extends: object /* Low-level zstd compression parameters. */ |
| `method` | **`from_level`** | `ZstdCompressionParameters` | L371-L399 | args: (level, source_size, dict_size) /* Create compression parameters from a com */ |
| `function` | **`__init__`** | `ZstdCompressionParameters` | L401-L489 | args: (self, format, compression_level, window_log) |
| `function` | **`format`** | `ZstdCompressionParameters` | L492-L493 | args: (self) |
| `function` | **`compression_level`** | `ZstdCompressionParameters` | L496-L499 | args: (self) |
| `function` | **`window_log`** | `ZstdCompressionParameters` | L502-L503 | args: (self) |
| `function` | **`hash_log`** | `ZstdCompressionParameters` | L506-L507 | args: (self) |
| `function` | **`chain_log`** | `ZstdCompressionParameters` | L510-L511 | args: (self) |
| `function` | **`search_log`** | `ZstdCompressionParameters` | L514-L515 | args: (self) |
| `function` | **`min_match`** | `ZstdCompressionParameters` | L518-L519 | args: (self) |
| `function` | **`target_length`** | `ZstdCompressionParameters` | L522-L523 | args: (self) |
| `function` | **`strategy`** | `ZstdCompressionParameters` | L526-L527 | args: (self) |
| `function` | **`write_content_size`** | `ZstdCompressionParameters` | L530-L533 | args: (self) |
| `function` | **`write_checksum`** | `ZstdCompressionParameters` | L536-L537 | args: (self) |
| `function` | **`write_dict_id`** | `ZstdCompressionParameters` | L540-L541 | args: (self) |
| `function` | **`job_size`** | `ZstdCompressionParameters` | L544-L545 | args: (self) |
| `function` | **`overlap_log`** | `ZstdCompressionParameters` | L548-L549 | args: (self) |
| `function` | **`force_max_window`** | `ZstdCompressionParameters` | L552-L555 | args: (self) |
| `function` | **`enable_ldm`** | `ZstdCompressionParameters` | L558-L561 | args: (self) |
| `function` | **`ldm_hash_log`** | `ZstdCompressionParameters` | L564-L565 | args: (self) |
| `function` | **`ldm_min_match`** | `ZstdCompressionParameters` | L568-L569 | args: (self) |
| `function` | **`ldm_bucket_size_log`** | `ZstdCompressionParameters` | L572-L575 | args: (self) |
| `function` | **`ldm_hash_rate_log`** | `ZstdCompressionParameters` | L578-L581 | args: (self) |
| `function` | **`threads`** | `ZstdCompressionParameters` | L584-L585 | args: (self) |
| `function` | **`estimated_compression_context_size`** | `ZstdCompressionParameters` | L587-L589 | args: (self) /* Estimated size in bytes needed to compre */ |
| `function` | **`estimate_decompression_context_size`** | `global` | L592-L598 | /* Estimate the memory size requirements fo */ |
| `function` | **`_set_compression_parameter`** | `global` | L601-L607 | args: (params, param, value) |
| `function` | **`_get_compression_parameter`** | `global` | L610-L620 | args: (params, param) |
| `class` | **`ZstdCompressionWriter`** | `global` | L623-L959 | extends: object /* Writable compressing stream wrapper. */ |
| `method` | **`__init__`** | `ZstdCompressionWriter` | L728-L757 | args: (self, compressor, writer, source_size) |
| `function` | **`__enter__`** | `ZstdCompressionWriter` | L759-L767 | args: (self) |
| `function` | **`__exit__`** | `ZstdCompressionWriter` | L769-L774 | args: (self, exc_type, exc_value, exc_tb) |
| `function` | **`__iter__`** | `ZstdCompressionWriter` | L776-L777 | args: (self) |
| `function` | **`__next__`** | `ZstdCompressionWriter` | L779-L780 | args: (self) |
| `function` | **`memory_size`** | `ZstdCompressionWriter` | L782-L783 | args: (self) |
| `function` | **`fileno`** | `ZstdCompressionWriter` | L785-L790 | args: (self) |
| `function` | **`close`** | `ZstdCompressionWriter` | L792-L806 | args: (self) |
| `function` | **`closed`** | `ZstdCompressionWriter` | L809-L810 | args: (self) |
| `function` | **`isatty`** | `ZstdCompressionWriter` | L812-L813 | args: (self) |
| `function` | **`readable`** | `ZstdCompressionWriter` | L815-L816 | args: (self) |
| `function` | **`readline`** | `ZstdCompressionWriter` | L818-L819 | args: (self, size) |
| `function` | **`readlines`** | `ZstdCompressionWriter` | L821-L822 | args: (self, hint) |
| `function` | **`seek`** | `ZstdCompressionWriter` | L824-L825 | args: (self, offset, whence) |
| `function` | **`seekable`** | `ZstdCompressionWriter` | L827-L828 | args: (self) |
| `function` | **`truncate`** | `ZstdCompressionWriter` | L830-L831 | args: (self, size) |
| `function` | **`writable`** | `ZstdCompressionWriter` | L833-L834 | args: (self) |
| `function` | **`writelines`** | `ZstdCompressionWriter` | L836-L837 | args: (self, lines) |
| `function` | **`read`** | `ZstdCompressionWriter` | L839-L840 | args: (self, size) |
| `function` | **`readall`** | `ZstdCompressionWriter` | L842-L843 | args: (self) |
| `function` | **`readinto`** | `ZstdCompressionWriter` | L845-L846 | args: (self, b) |
| `function` | **`write`** | `ZstdCompressionWriter` | L848-L888 | args: (self, data) /* Send data to the compressor and possibly */ |
| `function` | **`flush`** | `ZstdCompressionWriter` | L890-L956 | args: (self, flush_mode) /* Evict data from compressor's internal st */ |
| `function` | **`tell`** | `ZstdCompressionWriter` | L958-L959 | args: (self) |
| `class` | **`ZstdCompressionObj`** | `global` | L962-L1138 | extends: object /* A compressor conforming to the API in Py */ |
| `method` | **`__init__`** | `ZstdCompressionObj` | L1020-L1029 | args: (self, compressor, write_size) |
| `function` | **`compress`** | `ZstdCompressionObj` | L1031-L1071 | args: (self, data) /* Send data to the compressor. */ |
| `function` | **`flush`** | `ZstdCompressionObj` | L1073-L1138 | args: (self, flush_mode) /* Emit data accumulated in the compressor  */ |
| `class` | **`ZstdCompressionChunker`** | `global` | L1141-L1318 | extends: object /* Compress data to uniformly sized chunks. */ |
| `method` | **`__init__`** | `ZstdCompressionChunker` | L1194-L1206 | args: (self, compressor, chunk_size) |
| `function` | **`compress`** | `ZstdCompressionChunker` | L1208-L1251 | args: (self, data) /* Feed new input data into the compressor. */ |
| `function` | **`flush`** | `ZstdCompressionChunker` | L1253-L1282 | args: (self) /* Flushes all data currently in the compre */ |
| `function` | **`finish`** | `ZstdCompressionChunker` | L1284-L1318 | args: (self) /* Signals the end of input data. */ |
| `class` | **`ZstdCompressionReader`** | `global` | L1321-L1736 | extends: object /* Readable compressing stream wrapper. */ |
| `method` | **`__init__`** | `ZstdCompressionReader` | L1388-L1401 | args: (self, compressor, source, read_size) |
| `function` | **`__enter__`** | `ZstdCompressionReader` | L1403-L1411 | args: (self) |
| `function` | **`__exit__`** | `ZstdCompressionReader` | L1413-L1419 | args: (self, exc_type, exc_value, exc_tb) |
| `function` | **`readable`** | `ZstdCompressionReader` | L1421-L1422 | args: (self) |
| `function` | **`writable`** | `ZstdCompressionReader` | L1424-L1425 | args: (self) |
| `function` | **`seekable`** | `ZstdCompressionReader` | L1427-L1428 | args: (self) |
| `function` | **`readline`** | `ZstdCompressionReader` | L1430-L1431 | args: (self) |
| `function` | **`readlines`** | `ZstdCompressionReader` | L1433-L1434 | args: (self) |
| `function` | **`write`** | `ZstdCompressionReader` | L1436-L1437 | args: (self, data) |
| `function` | **`writelines`** | `ZstdCompressionReader` | L1439-L1440 | args: (self, ignored) |
| `function` | **`isatty`** | `ZstdCompressionReader` | L1442-L1443 | args: (self) |
| `function` | **`flush`** | `ZstdCompressionReader` | L1445-L1446 | args: (self) |
| `function` | **`close`** | `ZstdCompressionReader` | L1448-L1456 | args: (self) |
| `function` | **`closed`** | `ZstdCompressionReader` | L1459-L1460 | args: (self) |
| `function` | **`tell`** | `ZstdCompressionReader` | L1462-L1463 | args: (self) |
| `function` | **`readall`** | `ZstdCompressionReader` | L1465-L1475 | args: (self) |
| `function` | **`__iter__`** | `ZstdCompressionReader` | L1477-L1478 | args: (self) |
| `function` | **`__next__`** | `ZstdCompressionReader` | L1480-L1481 | args: (self) |
| `function` | **`_read_input`** | `ZstdCompressionReader` | L1485-L1504 | args: (self) |
| `function` | **`_compress_into_buffer`** | `ZstdCompressionReader` | L1506-L1533 | args: (self, out_buffer) |
| `function` | **`read`** | `ZstdCompressionReader` | L1535-L1581 | args: (self, size) |
| `function` | **`read1`** | `ZstdCompressionReader` | L1583-L1647 | args: (self, size) |
| `function` | **`readinto`** | `ZstdCompressionReader` | L1649-L1688 | args: (self, b) |
| `function` | **`readinto1`** | `ZstdCompressionReader` | L1690-L1736 | args: (self, b) |
| `class` | **`ZstdCompressor`** | `global` | L1739-L2490 | extends: object /* Create an object used to perform Zstanda */ |
| `method` | **`__init__`** | `ZstdCompressor` | L1807-L1894 | args: (self, level, dict_data, compression_params) |
| `function` | **`_setup_cctx`** | `ZstdCompressor` | L1896-L1924 | args: (self) |
| `function` | **`memory_size`** | `ZstdCompressor` | L1926-L1932 | args: (self) /* Obtain the memory usage of this compress */ |
| `function` | **`compress`** | `ZstdCompressor` | L1934-L1987 | args: (self, data) /* Compress data in a single operation. */ |
| `function` | **`compressobj`** | `ZstdCompressor` | L1989-L2013 | args: (self, size) /* Obtain a compressor exposing the Python  */ |
| `function` | **`chunker`** | `ZstdCompressor` | L2015-L2040 | args: (self, size, chunk_size) /* Create an object for iterative compressi */ |
| `function` | **`copy_stream`** | `ZstdCompressor` | L2042-L2162 | args: (self, ifh, ofh, size) /* Copy data between 2 streams while compre */ |
| `function` | **`stream_reader`** | `ZstdCompressor` | L2164-L2212 | args: (self, source, size, read_size) /* Wrap a readable source with a stream tha */ |
| `function` | **`stream_writer`** | `ZstdCompressor` | L2214-L2259 | args: (self, writer, size, write_size) /* Create a stream that will write compress */ |
| `function` | **`read_to_iter`** | `ZstdCompressor` | L2261-L2428 | args: (self, reader, size, read_size) /* Read uncompressed data from a reader and */ |
| `function` | **`multi_compress_to_buffer`** | `ZstdCompressor` | L2430-L2477 | args: (self, data, threads) /* Compress multiple pieces of data as a si */ |
| `function` | **`frame_progression`** | `ZstdCompressor` | L2479-L2490 | args: (self) /* Return information on how much work the  */ |
| `class` | **`FrameParameters`** | `global` | L2493-L2520 | extends: object /* Information about a zstd frame. */ |
| `method` | **`__init__`** | `FrameParameters` | L2516-L2520 | args: (self, fparams) |
| `function` | **`frame_content_size`** | `global` | L2523-L2541 | args: (data) /* Obtain the decompressed size of a frame. */ |
| `function` | **`frame_header_size`** | `global` | L2544-L2558 | args: (data) /* Obtain the size of a frame header. */ |
| `function` | **`get_frame_parameters`** | `global` | L2561-L2593 | args: (data, format) /* Parse a zstd frame header into frame par */ |
| `class` | **`ZstdCompressionDict`** | `global` | L2596-L2766 | extends: object /* Represents a computed compression dictio */ |
| `method` | **`__init__`** | `ZstdCompressionDict` | L2677-L2694 | args: (self, data, dict_type, k) |
| `function` | **`__len__`** | `ZstdCompressionDict` | L2696-L2697 | args: (self) |
| `function` | **`dict_id`** | `ZstdCompressionDict` | L2699-L2701 | args: (self) /* Obtain the integer ID of the dictionary. */ |
| `function` | **`as_bytes`** | `ZstdCompressionDict` | L2703-L2705 | args: (self) /* Obtain the ``bytes`` representation of t */ |
| `function` | **`precompute_compress`** | `ZstdCompressionDict` | L2707-L2746 | args: (self, level, compression_params) /* Precompute a dictionary os it can be use */ |
| `function` | **`_ddict`** | `ZstdCompressionDict` | L2749-L2766 | args: (self) |
| `function` | **`train_dictionary`** | `global` | L2769-L2909 | args: (dict_size, samples, k, d) /* Train a dictionary from sample data usin */ |
| `class` | **`ZstdDecompressionObj`** | `global` | L2912-L3063 | extends: object /* A standard library API compatible decomp */ |
| `method` | **`__init__`** | `ZstdDecompressionObj` | L2949-L2954 | args: (self, decompressor, write_size, read_across_frames) |
| `function` | **`decompress`** | `ZstdDecompressionObj` | L2956-L3031 | args: (self, data) /* Send compressed data to the decompressor */ |
| `function` | **`flush`** | `ZstdDecompressionObj` | L3033-L3043 | args: (self, length) /* Effectively a no-op. */ |
| `function` | **`unused_data`** | `ZstdDecompressionObj` | L3046-L3053 | args: (self) /* Bytes past the end of compressed data. */ |
| `function` | **`unconsumed_tail`** | `ZstdDecompressionObj` | L3056-L3058 | args: (self) /* Data that has not yet been fed into the  */ |
| `function` | **`eof`** | `ZstdDecompressionObj` | L3061-L3063 | args: (self) /* Whether the end of the compressed data s */ |
| `class` | **`ZstdDecompressionReader`** | `global` | L3066-L3450 | extends: object /* Read only decompressor that pull uncompr */ |
| `method` | **`__init__`** | `ZstdDecompressionReader` | L3129-L3149 | args: (self, decompressor, source, read_size) |
| `function` | **`__enter__`** | `ZstdDecompressionReader` | L3151-L3159 | args: (self) |
| `function` | **`__exit__`** | `ZstdDecompressionReader` | L3161-L3167 | args: (self, exc_type, exc_value, exc_tb) |
| `function` | **`readable`** | `ZstdDecompressionReader` | L3169-L3170 | args: (self) |
| `function` | **`writable`** | `ZstdDecompressionReader` | L3172-L3173 | args: (self) |
| `function` | **`seekable`** | `ZstdDecompressionReader` | L3175-L3176 | args: (self) |
| `function` | **`readline`** | `ZstdDecompressionReader` | L3178-L3179 | args: (self, size) |
| `function` | **`readlines`** | `ZstdDecompressionReader` | L3181-L3182 | args: (self, hint) |
| `function` | **`write`** | `ZstdDecompressionReader` | L3184-L3185 | args: (self, data) |
| `function` | **`writelines`** | `ZstdDecompressionReader` | L3187-L3188 | args: (self, lines) |
| `function` | **`isatty`** | `ZstdDecompressionReader` | L3190-L3191 | args: (self) |
| `function` | **`flush`** | `ZstdDecompressionReader` | L3193-L3194 | args: (self) |
| `function` | **`close`** | `ZstdDecompressionReader` | L3196-L3204 | args: (self) |
| `function` | **`closed`** | `ZstdDecompressionReader` | L3207-L3208 | args: (self) |
| `function` | **`tell`** | `ZstdDecompressionReader` | L3210-L3211 | args: (self) |
| `function` | **`readall`** | `ZstdDecompressionReader` | L3213-L3223 | args: (self) |
| `function` | **`__iter__`** | `ZstdDecompressionReader` | L3225-L3226 | args: (self) |
| `function` | **`__next__`** | `ZstdDecompressionReader` | L3228-L3229 | args: (self) |
| `function` | **`_read_input`** | `ZstdDecompressionReader` | L3233-L3258 | args: (self) |
| `function` | **`_decompress_into_buffer`** | `ZstdDecompressionReader` | L3260-L3288 | args: (self, out_buffer) /* Decompress available input into an outpu */ |
| `function` | **`read`** | `ZstdDecompressionReader` | L3290-L3324 | args: (self, size) |
| `function` | **`readinto`** | `ZstdDecompressionReader` | L3326-L3353 | args: (self, b) |
| `function` | **`read1`** | `ZstdDecompressionReader` | L3355-L3387 | args: (self, size) |
| `function` | **`readinto1`** | `ZstdDecompressionReader` | L3389-L3413 | args: (self, b) |
| `function` | **`seek`** | `ZstdDecompressionReader` | L3415-L3450 | args: (self, pos, whence) |
| `class` | **`ZstdDecompressionWriter`** | `global` | L3453-L3658 | extends: object /* Write-only stream wrapper that performs  */ |
| `method` | **`__init__`** | `ZstdDecompressionWriter` | L3502-L3519 | args: (self, decompressor, writer, write_size) |
| `function` | **`__enter__`** | `ZstdDecompressionWriter` | L3521-L3530 | args: (self) |
| `function` | **`__exit__`** | `ZstdDecompressionWriter` | L3532-L3536 | args: (self, exc_type, exc_value, exc_tb) |
| `function` | **`__iter__`** | `ZstdDecompressionWriter` | L3538-L3539 | args: (self) |
| `function` | **`__next__`** | `ZstdDecompressionWriter` | L3541-L3542 | args: (self) |
| `function` | **`memory_size`** | `ZstdDecompressionWriter` | L3544-L3545 | args: (self) |
| `function` | **`close`** | `ZstdDecompressionWriter` | L3547-L3560 | args: (self) |
| `function` | **`closed`** | `ZstdDecompressionWriter` | L3563-L3564 | args: (self) |
| `function` | **`fileno`** | `ZstdDecompressionWriter` | L3566-L3571 | args: (self) |
| `function` | **`flush`** | `ZstdDecompressionWriter` | L3573-L3579 | args: (self) |
| `function` | **`isatty`** | `ZstdDecompressionWriter` | L3581-L3582 | args: (self) |
| `function` | **`readable`** | `ZstdDecompressionWriter` | L3584-L3585 | args: (self) |
| `function` | **`readline`** | `ZstdDecompressionWriter` | L3587-L3588 | args: (self, size) |
| `function` | **`readlines`** | `ZstdDecompressionWriter` | L3590-L3591 | args: (self, hint) |
| `function` | **`seek`** | `ZstdDecompressionWriter` | L3593-L3594 | args: (self, offset, whence) |
| `function` | **`seekable`** | `ZstdDecompressionWriter` | L3596-L3597 | args: (self) |
| `function` | **`tell`** | `ZstdDecompressionWriter` | L3599-L3600 | args: (self) |
| `function` | **`truncate`** | `ZstdDecompressionWriter` | L3602-L3603 | args: (self, size) |
| `function` | **`writable`** | `ZstdDecompressionWriter` | L3605-L3606 | args: (self) |
| `function` | **`writelines`** | `ZstdDecompressionWriter` | L3608-L3609 | args: (self, lines) |
| `function` | **`read`** | `ZstdDecompressionWriter` | L3611-L3612 | args: (self, size) |
| `function` | **`readall`** | `ZstdDecompressionWriter` | L3614-L3615 | args: (self) |
| `function` | **`readinto`** | `ZstdDecompressionWriter` | L3617-L3618 | args: (self, b) |
| `function` | **`write`** | `ZstdDecompressionWriter` | L3620-L3658 | args: (self, data) |
| `class` | **`ZstdDecompressor`** | `global` | L3661-L4478 | extends: object /* Context for performing zstandard decompr */ |
| `method` | **`__init__`** | `ZstdDecompressor` | L3703-L3721 | args: (self, dict_data, max_window_size, format) |
| `function` | **`memory_size`** | `ZstdDecompressor` | L3723-L3729 | args: (self) /* Size of decompression context, in bytes. */ |
| `function` | **`decompress`** | `ZstdDecompressor` | L3731-L3875 | args: (self, data, max_output_size, read_across_frames) /* Decompress data in a single operation. */ |
| `function` | **`stream_reader`** | `ZstdDecompressor` | L3877-L3912 | args: (self, source, read_size, read_across_frames) /* Read-only stream wrapper that performs d */ |
| `function` | **`decompressobj`** | `ZstdDecompressor` | L3914-L3938 | args: (self, write_size, read_across_frames) /* Obtain a standard library compatible inc */ |
| `function` | **`read_to_iter`** | `ZstdDecompressor` | L3940-L4084 | args: (self, reader, read_size, write_size) /* Read compressed data to an iterator of u */ |
| `function` | **`stream_writer`** | `ZstdDecompressor` | L4088-L4128 | args: (self, writer, write_size, write_return_read) /* Push-based stream wrapper that performs  */ |
| `function` | **`copy_stream`** | `ZstdDecompressor` | L4130-L4223 | args: (self, ifh, ofh, read_size) /* Copy data between streams, decompressing */ |
| `function` | **`decompress_content_dict_chain`** | `ZstdDecompressor` | L4225-L4372 | args: (self, frames) /* Decompress a series of frames using the  */ |
| `function` | **`multi_decompress_to_buffer`** | `ZstdDecompressor` | L4374-L4450 | args: (self, frames, decompressed_sizes, threads) /* Decompress multiple zstd frames to outpu */ |
| `function` | **`_ensure_dctx`** | `ZstdDecompressor` | L4452-L4478 | args: (self, load_dict) |

