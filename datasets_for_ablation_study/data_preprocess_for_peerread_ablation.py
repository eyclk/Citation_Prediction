import pandas as pd
from transformers import RobertaTokenizer


contexts_file = "../data_preprocessing/peerread_original/contexts.json"
papers_file = "../data_preprocessing/peerread_original/papers.json"

dataset_output_file = "peerread_ablation/context_dataset.csv"
vocab_output_file = "peerread_ablation/additions_to_vocab.csv"
train_set_output_file = "peerread_ablation/context_dataset_train.csv"
eval_set_output_file = "peerread_ablation/context_dataset_eval.csv"

# IMPORTANT: Max token limit has been selected as 400 !!!!!


def create_target_token_for_ref_paper_id(ref_id, papers_df):
    temp_paper_info_row = papers_df[ref_id]
    year_from_paper_info = str(int(float(temp_paper_info_row['year'])))
    authors_from_paper_info = temp_paper_info_row['authors']

    target_cit_token = ""
    if len(authors_from_paper_info) == 1:
        target_cit_token = authors_from_paper_info[0].split(" ")[-1].capitalize() + ", " + year_from_paper_info
    elif len(authors_from_paper_info) == 2:
        target_cit_token = authors_from_paper_info[0].split(" ")[-1].capitalize() + " and " + \
                           authors_from_paper_info[1].split(" ")[-1].capitalize() + ", " + year_from_paper_info
    elif len(authors_from_paper_info) > 2:
        target_cit_token = authors_from_paper_info[0].split(" ")[-1].capitalize() + " et al., " + year_from_paper_info

    return target_cit_token


def preprocess_dataset():
    contexts_df = pd.read_json(contexts_file)
    papers_df = pd.read_json(papers_file)

    cit_contexts_list = []
    masked_cit_contexts_list = []
    masked_token_target_list = []

    context_df_length = len(contexts_df.columns)
    for i in range(context_df_length):
        temp_context_row = contexts_df.iloc[:, i]

        temp_target_token = create_target_token_for_ref_paper_id(temp_context_row['refid'], papers_df)

        masked_text_global, unmasked_text_global = concatenate_title_and_abstract_while_making_context_shorter(
            temp_target_token, temp_context_row['refid'], papers_df)

        masked_cit_contexts_list.append(masked_text_global)
        masked_token_target_list.append(temp_target_token)
        cit_contexts_list.append(unmasked_text_global)

    # count_unmasked_contexts_with_more_than_k_tokens(cit_contexts_list, k=400)

    new_df_table = pd.DataFrame({'citation_context': cit_contexts_list, 'masked_cit_context': masked_cit_contexts_list,
                                 'masked_token_target': masked_token_target_list})
    new_df_table.to_csv(dataset_output_file)

    citations_for_vocab = list(set(masked_token_target_list))
    vocab_additions = pd.DataFrame({'additions_to_vocab': citations_for_vocab})
    vocab_additions.to_csv(vocab_output_file)

    print("--> Length of whole set: ", len(cit_contexts_list))
    print("--> Additional vocab size: ", len(citations_for_vocab), "\n")


# IMPORTANT: Default max_token_limit have been reduced to 400!!!
def concatenate_title_and_abstract_while_making_context_shorter(temp_target, ref_id,
                                                                papers_df, max_token_limit=400):
    temp_title = papers_df[ref_id]["title"]
    temp_abstract = papers_df[ref_id]["abstract"]

    masked_with_global_info = "<mask> </s> " + temp_title + " </s> " + temp_abstract
    tokenized_with_global_info_masked = tokenizer.tokenize(masked_with_global_info)
    if len(tokenized_with_global_info_masked) > max_token_limit:
        trimmed_tokenized_with_global_info_masked = tokenized_with_global_info_masked[:max_token_limit]
        masked_with_global_info = tokenizer.convert_tokens_to_string(trimmed_tokenized_with_global_info_masked)

    unmasked_with_global_info = temp_target + " </s> " + temp_title + " </s> " + temp_abstract
    tokenized_with_global_info_unmasked = tokenizer.tokenize(unmasked_with_global_info)
    if len(tokenized_with_global_info_unmasked) > max_token_limit:
        trimmed_tokenized_with_global_info_unmasked = tokenized_with_global_info_unmasked[:max_token_limit]
        unmasked_with_global_info = tokenizer.convert_tokens_to_string(
            trimmed_tokenized_with_global_info_unmasked)

    return masked_with_global_info, unmasked_with_global_info


def split_dataset():
    contexts_df = pd.read_csv(dataset_output_file)

    # Shuffle the DataFrame rows
    contexts_df = contexts_df.sample(frac=1)

    split_threshold = int(len(contexts_df) * 80 / 100)  # I have selected 20% as the eval set.

    # Split the df into train and eval sets
    df_train = contexts_df.iloc[:split_threshold, 1:]
    df_eval = contexts_df.iloc[split_threshold:, 1:]

    print("--> Length of train set: ", len(df_train))
    print("--> Length of eval set: ", len(df_eval))

    df_train.to_csv(train_set_output_file, index=False)
    df_eval.to_csv(eval_set_output_file, index=False)


tokenizer = RobertaTokenizer.from_pretrained("roberta-base", truncation=True, padding='max_length', max_length=400)


def count_unmasked_contexts_with_more_than_k_tokens(unmasked_cit_contexts, k=400):
    more_than_k_count = 0
    for m in unmasked_cit_contexts:
        tokenized_masked_text = tokenizer.tokenize(m)
        if len(tokenized_masked_text) > k:
            more_than_k_count += 1
    print(f"--->> Number of unmasked contexts with more than {k} tokens =", more_than_k_count, "\n")


if __name__ == '__main__':
    preprocess_dataset()

    split_dataset()
