import os
import re
import sys

from urllib.parse import urlparse
import tiktoken
import pandas as pd
import openai

CRAWLED_PAGES = "output/"
IGNORE_TEST_FILES = False


def remove_newlines(content):
    content = content.str.replace('\n', ' ')
    content = content.str.replace('\\n', ' ')
    content = content.str.replace('  ', ' ')
    content = content.str.replace('  ', ' ')
    return content


def process_git_folder(git_folder_path, ignore_test_files=True):
    texts = []

    for root, _, files in os.walk(git_folder_path):
        for file in files:
            if file.endswith(".go"):
                # Ignore test files if the flag is set to True
                if ignore_test_files and file.endswith("_test.go"):
                    continue

                file_path = os.path.join(root, file)

                with open(file_path, "r", encoding="UTF-8") as go_file:
                    go_content = go_file.read()

                    texts.append((file, go_content))

    data_frame = pd.DataFrame(texts, columns=['fname', 'text'])
    data_frame['text'] = data_frame.fname + ". " + remove_newlines(data_frame.text)

    return data_frame


def process_website(url):
    domain = urlparse(url).hostname

    # Create a list to store the web text files
    texts = []

    # Get all the web text files in the web text directory
    for file in os.listdir(CRAWLED_PAGES + domain + "/"):
        # Open the file and read the web text
        with open(CRAWLED_PAGES + domain + "/" + file, "r", encoding="UTF-8") as web_file:
            web_text = web_file.read()

            # Omit the first 11 lines and the last 4 lines, then replace -, _, and #update with spaces.
            texts.append((file[11:-4].replace('-', ' ').replace('_', ' ').replace('#update', ''), web_text))

    # Create a dataframe from the list of texts
    data_frame = pd.DataFrame(texts, columns=['fname', 'text'])

    # Set the web_text column to be the raw web_text with the newlines removed
    data_frame['text'] = data_frame.fname + ". " + remove_newlines(data_frame.text)

    return data_frame


def is_url(url):
    pattern = re.compile(r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return bool(pattern.match(url))


if len(sys.argv) != 2:
    print("Usage: python main.py <config_file>")
    sys.exit(1)

config_file = sys.argv[1]

# Read the configuration file
with open(config_file, "r") as f:
    config_lines = [line.strip() for line in f.readlines()]

# Remove empty lines
config_lines = [line for line in config_lines if line]

# Check if the topic property exists
topic = None
for line in config_lines:
    if line.startswith("topic:"):
        topic = line.split(":", 1)[1].strip()
        break

if topic is None:
    print("Error: The topic property does not exist in the config file.")
    sys.exit(1)

# Process each configuration line (website URL or local Git folder path)
dfs = []
# Initialize a flag to check if the topic line has been processed
topic_line_read = False
for line in config_lines:
    if not topic_line_read:
        # Ignore the first non-empty line, which is the topic line
        topic_line_read = True
        continue

    if is_url(line):
        print("Processing website: " + line + "...")
        site_text = process_website(line)
        df = pd.DataFrame({'fname': [urlparse(line).hostname], 'text': [site_text]})
        dfs.append(df)
    else:
        print("Processing Git folder: " + line + "...")
        df = process_git_folder(line, )
        dfs.append(df)

# Combine all data frames
combined_df = pd.concat(dfs, ignore_index=True)
csv_filename = f"processed/{topic}.csv"
combined_df.to_csv(csv_filename)
print(f"Saved combined data frames to {csv_filename}")

# Tokenize
# Load the cl100k_base tokenizer which is designed to work with the ada-002 model
tokenizer = tiktoken.get_encoding("cl100k_base")

df = pd.read_csv(csv_filename, index_col=0)
df.columns = ['title', 'text']

# Tokenize the text and save the number of tokens to a new column
df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))

# Visualize the distribution of the number of tokens per row using a histogram
df.n_tokens.hist()

MAX_TOKENS = 500


# Function to split the text into chunks of a maximum number of tokens
def split_into_many(text, max_tokens_in=MAX_TOKENS):
    # Split the text into sentences
    sentences = text.split('. ')

    # Get the number of tokens for each sentence
    n_tokens = [len(tokenizer.encode(" " + sentence)) for sentence in sentences]

    chunks = []
    tokens_so_far = 0
    chunk = []

    # Loop through the sentences and tokens joined together in a tuple
    for sentence, token in zip(sentences, n_tokens):

        # If the number of tokens so far plus the number of tokens in the current sentence is greater
        # than the max number of tokens, then add the chunk to the list of chunks and reset
        # the chunk and tokens so far
        if tokens_so_far + token > max_tokens_in:
            chunks.append(". ".join(chunk) + ".")
            chunk = []
            tokens_so_far = 0

        # If the number of tokens in the current sentence is greater than the max number of
        # tokens, go to the next sentence
        if token > max_tokens_in:
            continue

        # Otherwise, add the sentence to the chunk and add the number of tokens to the total
        chunk.append(sentence)
        tokens_so_far += token + 1

    return chunks


shortened = []

# Loop through the dataframe
for row in df.iterrows():

    # If the text is None, go to the next row
    if row[1]['text'] is None:
        continue

    # If the number of tokens is greater than the max number of tokens, split the text into chunks
    if row[1]['n_tokens'] > MAX_TOKENS:
        shortened += split_into_many(row[1]['text'])

    # Otherwise, add the text to the list of shortened texts
    else:
        shortened.append(row[1]['text'])

df = pd.DataFrame(shortened, columns=['text'])
df['n_tokens'] = df.text.apply(lambda x: len(tokenizer.encode(x)))
df.n_tokens.hist()

print("Completed tokenization.")

embeddings_filename = f"processed/{topic}_embeddings.csv"
df[embeddings_filename] = df.text.apply(
    lambda x: openai.Embedding.create(input=x, engine='text-embedding-ada-002')['data'][0]['embedding'])

df.to_csv(embeddings_filename)
print(f"Saved combined data frames to {embeddings_filename}")
print(df.head())
