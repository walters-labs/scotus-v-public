"""Optional quantized query encoder; loaded only by optional search modes."""
from pathlib import Path
import threading

class Encoder:
    def __init__(self, folder):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_file(str(Path(folder)/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(Path(folder)/'model.onnx'),
            sess_options=options, providers=['CPUExecutionProvider'])
        self.lock = threading.Lock()

    def encode(self, texts):
        import numpy as np
        # Tokenizer padding settings and inference share one bounded workspace.
        with self.lock:
            encoded = self.tokenizer.encode_batch(texts)
            mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            inputs = dict(input_ids=np.array([e.ids for e in encoded], dtype=np.int64),
                attention_mask=mask,
                token_type_ids=np.array([e.type_ids for e in encoded], dtype=np.int64))
            hidden = self.session.run(None, inputs)[0]
            vectors = (hidden*mask[:, :, None]).sum(1)/mask.sum(1)[:, None]
            vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
            return vectors.astype('float32')

