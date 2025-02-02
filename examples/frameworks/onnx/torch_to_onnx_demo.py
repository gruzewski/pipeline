import onnxruntime
import torch
from torch import nn

from pipeline.util.torch_utils import tensor_to_list


# demo pytorch model
class NeuralNetwork(nn.Module):
    def __init__(self):
        super(NeuralNetwork, self).__init__()
        self.flatten = nn.Flatten()
        self.linear = nn.Linear(28 * 28, 10)

    def forward(self, x):
        x = self.flatten(x)
        logits = self.linear(x)
        return logits


# run pytorch inference
model = NeuralNetwork().cpu()
dummy_input = torch.rand(1, 28, 28, device="cpu")
pytorch_output = tensor_to_list(model(dummy_input))

# convert to onnx
input_names = ["input"]
output_names = ["output"]
torch.onnx.export(
    model,
    dummy_input,
    "example.onnx",
    verbose=True,
    input_names=input_names,
    output_names=output_names,
)

# run onnx inference

session = onnxruntime.InferenceSession(
    "example.onnx",
    providers=[
        "CUDAExecutionProvider",
    ],
)

onnx_output = session.run(output_names, {"input": tensor_to_list(dummy_input)})[
    0
].tolist()

# compare onnx and pytorch outputs
print(pytorch_output, onnx_output, sep="\n")
