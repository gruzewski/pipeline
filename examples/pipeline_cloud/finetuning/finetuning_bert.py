""" Finetuning example with bert

Code adapted from:
https://huggingface.co/docs/transformers/training#train-in-native-pytorch

Dependencies:
datasets==2.7.1


"""


from datasets import DatasetDict, load_dataset

from pipeline import Pipeline, PipelineCloud, Variable, pipeline_function
from pipeline.schemas.run import RunState


@pipeline_function
def preprocessing(dataset: DatasetDict) -> list:
    from torch.utils.data import DataLoader
    from transformers import AutoTokenizer

    # Tokenize and reformt the dataset for use in pytorch

    tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True)

    tokenized_datasets = dataset.map(tokenize_function, batched=True)
    tokenized_datasets = tokenized_datasets.remove_columns(["text"])

    tokenized_datasets = tokenized_datasets.rename_column("label", "labels")
    tokenized_datasets.set_format("torch")

    small_train_dataset = (
        tokenized_datasets["train"].shuffle(seed=42).select(range(100))
    )
    small_eval_dataset = tokenized_datasets["test"].shuffle(seed=42).select(range(100))

    train_dataloader = DataLoader(small_train_dataset, shuffle=True, batch_size=8)
    eval_dataloader = DataLoader(small_eval_dataset, batch_size=8)

    return [train_dataloader, eval_dataloader]


@pipeline_function
def training_loop(dataloaders: list, training_args: dict) -> str:
    import torch
    from torch.optim import AdamW
    from tqdm.auto import tqdm
    from transformers import AutoModelForSequenceClassification, get_scheduler

    (train_dataloader, eval_dataloader) = dataloaders

    model = AutoModelForSequenceClassification.from_pretrained(
        "bert-base-cased", num_labels=5
    )

    optimizer = AdamW(model.parameters(), lr=5e-5)

    num_epochs = 5
    num_training_steps = num_epochs * len(train_dataloader)
    lr_scheduler = get_scheduler(
        name="linear",
        optimizer=optimizer,
        num_warmup_steps=0,
        num_training_steps=num_training_steps,
    )

    device = (
        torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
    )
    model.to(device)

    progress_bar = tqdm(range(num_training_steps))

    model.train()
    for epoch in range(num_epochs):
        for batch in train_dataloader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()

            optimizer.step()
            lr_scheduler.step()
            optimizer.zero_grad()
            progress_bar.update(1)

    model.eval()
    for batch in eval_dataloader:
        batch = {k: v.to(device) for k, v in batch.items()}
        with torch.no_grad():
            outputs = model(**batch)

        logits = outputs.logits
        torch.argmax(logits, dim=-1)

    return model


with Pipeline("bert-finetune") as builder:
    input_dataset = Variable(DatasetDict, is_input=True)
    training_args = Variable(dict, is_input=True)
    builder.add_variables(input_dataset, training_args)

    data_loaders = preprocessing(input_dataset)
    output_model = training_loop(data_loaders, training_args)

    builder.output(output_model)


finetune_pl = Pipeline.get_pipeline("bert-finetune")


dataset = load_dataset("yelp_review_full")
training_args = dict(num_epochs=3)
# from transformers import AutoTokenizer

# print(dataset)
# # print(len(dataset["train"]["label"]))
# # print(len(dataset["train"]["text"][1]))
# tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")


# def tokenize_function(examples):
#     return tokenizer(examples["text"], padding="max_length", truncation=True)


# tokenized_datasets = dataset.map(tokenize_function, batched=True)

# print(tokenized_datasets["train"]["text"][0])

# exit()

run_remote = False
pcloud = PipelineCloud()

if run_remote:
    uploaded_pipeline = pcloud.upload_pipeline(finetune_pl)

    result_run = pcloud.run_pipeline(uploaded_pipeline, [dataset, training_args])
    print(f"Run:{result_run.id}:{result_run.run_state}")

    if result_run.run_state == RunState.FAILED:
        print(result_run.error_info)
else:
    pcloud.download_remotes(finetune_pl)
    output = finetune_pl.run(dataset, training_args)
