import sys

import numpy as np
import openai
import pandas as pd
from openai.embeddings_utils import distances_from_embeddings

QA_GPT_MODEL = "gpt-3.5-turbo"

if len(sys.argv) != 2:
    print("Usage: python qa.py <embeddings_csv_filename>")
    sys.exit(1)

embeddings_csv_filename = sys.argv[1]
g_full_path = f"processed/{embeddings_csv_filename}"

df = pd.read_csv(g_full_path, index_col=0)
df[g_full_path] = df[g_full_path].apply(eval).apply(np.array)

print(df.head())


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
    for _, row in data_frame.sort_values('distances', ascending=True).iterrows():

        # Add the length of the text to the current length
        cur_len += row['n_tokens'] + 4

        # If the context is too long, break
        if cur_len > max_len:
            break

        # Else add it to the text that is being returned
        returns.append(row["text"])

    # Return the context
    return "\n\n###\n\n".join(returns)


def answer_question(data_frame, model="gpt-3.5-turbo",
                    question="Am I allowed to publish model outputs to Twitter, without a human review?", max_len=1800,
                    debug=False, max_tokens=150, stop_sequence=None):
    """
    Answer a question based on the most similar context from the dataframe texts
    """

    context = create_context(question, data_frame, max_len=max_len)

    # If debug, print the raw model response
    if debug:
        print("Context:\n" + context)
        print("\n\n")

    try:
        # Create a list of messages
        messages = [
            {"role": "system", "content": "You are an AI that answers questions based on the provided context."},
            {"role": "user", "content": f"Context: {context}\n\n---\n\nQuestion: {question}\nAnswer:"}
        ]

        # Create a chat completion using the messages
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            n=1,
            stop=stop_sequence,
            temperature=0
        )

        return response.choices[0].message['content'].strip()
    except Exception as e:
        print(e)
        return ""


print(answer_question(df, QA_GPT_MODEL, question="What day is it?", debug=False))
print()
print(answer_question(df, QA_GPT_MODEL, question="What is op stack?"))
print()
print(answer_question(df, QA_GPT_MODEL, question="What is ethereum equivalence?"))
