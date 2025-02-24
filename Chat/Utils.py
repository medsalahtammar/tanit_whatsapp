# Import the Retriever module from the current directory
from Retriever import hybridCypherRetriever

# Define the retrieve_info function
def retrieve_info(question):
    return hybridCypherRetriever(question)
