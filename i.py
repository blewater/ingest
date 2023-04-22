import ast
import numpy as np
import openai
import pandas as pd
from openai.embeddings_utils import distances_from_embeddings

GPT_3_5_TURBO = "gpt-3.5-turbo"

# This file is meant for interactive mode, so we don't need to pass in a filename
# call load_data() to load the data from a file
g_full_path = None

# Total for GPT-3.5-turbo: 4096
MAX_LEN = 2896
MAX_TOKENS = 1200

# For future use
size = "ada"


def create_context(question, data_frame, max_len=1800):
    """
    Create a context for a question by finding the most similar context from the dataframe
    """

    # Get the embeddings for the question
    q_embeddings = openai.Embedding.create(input=question, engine='text-embedding-ada-002')['data'][0]['embedding']

    # Get the distances from the embeddings
    data_frame['distances'] = distances_from_embeddings(q_embeddings, data_frame['embeddings'].values,
                                                        distance_metric='cosine')

    returns = []
    cur_len = 0

    # Sort by distance and add the text to the context until the context is too long
    for i, row in data_frame.sort_values('distances', ascending=True).iterrows():

        # Add the length of the text to the current length
        cur_len += row['n_tokens'] + 4

        # If the context is too long, break
        if cur_len > max_len:
            break

        # Else add it to the text that is being returned
        returns.append(row["text"])

    # Return the context
    return "\n\n###\n\n".join(returns)


def answer_question(data_frame, model=GPT_3_5_TURBO,
                    question="Am I allowed to publish model outputs to Twitter, without a human review?",
                    max_len_in=MAX_LEN, debug=False, max_tokens_in=MAX_TOKENS, stop_sequence=None):
    """
    Answer a question based on the most similar context from the dataframe texts
    """
    context = create_context(question, data_frame, max_len=max_len_in)
    # If debug, print the raw model response
    if debug:
        print("Context:\n" + context)
        print("\n\n")

    try:
        # Create a list of messages
        messages = [
            {"role": "system", "content": "You are an AI that answers questions based on the provided context."},
            {"role": "system", "content": "Let's think step by step."},
            {"role": "system", "content": "Respond as an expert."},
            {"role": "user", "content": f"Context: {context}\n\n---\n\nQuestion: {question}\nAnswer:"}
        ]

        # Create a chat completion using the messages
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens_in,
            n=1,
            stop=stop_sequence,
            temperature=0.8,
        )

        return response.choices[0].message['content'].strip()
    except Exception as e:
        print(e)
        return ""


def load_data(filename):
    full_path = f'processed/{filename}_embeddings.csv'
    print("Loading data from ", full_path, "...")
    df = pd.read_csv(full_path, index_col=0)

    # Use the 'text' column for processing
    df['embeddings'] = df['embeddings'].apply(ast.literal_eval).apply(np.array)

    return df
