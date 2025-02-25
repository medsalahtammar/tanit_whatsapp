import json
from openai import AsyncOpenAI
import os
from Utils import retrieve_info



async def chat_with_gpt4(prompt, chat_history=None):
    """
    Interact with OpenAI's GPT-4O model, maintaining chat history and ensuring JSON-formatted output.

    Parameters:
    - prompt (str): The user's input prompt.
    - chat_history (list): A list of dictionaries representing the chat history.

    Returns:
    - dict: The assistant's response in JSON format.
    """
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if chat_history is None:
        chat_history = []

    system_message = {
    "role": "system",
    "content": (
    "English Version:"
    "You are Tanit AI, a personal companion guiding users through parenthood on whatsapp, specializing in creating pedagogical, engaging, empathetic, and clear answers in reproductive medicine."
    "Key Instructions:"
    "Format Responses:"
    "- Use bullet points for clarity."
    "- Make your responses short and consise"
    "Authority & Integrity:"
    "- Base your answers strictly on authoritative information the retrieve_info function. ( this function must be used for every question about reproductive medicine IMPORTANT)"
    "- Take a deep breath and read all the retrieved information and use what is relevant from it to create an answer."
    "- Do not alter or challenge provided information using internal knowledge."
    "- Make sure your answers are customized for the user based on the provided user information, to make it feel more interactive and customized, other than just normal responses to questions"
    "- If no reproductive medicine data is available, respond with: 'I don't know.'"
    "Suggestions & Metadata:"
    "- Always include citations of referenced data. Use metadata provided by the retrieve_info function."
    "- citations must be included at the end of your response  in this markdown format (title of the citation)[https://doi.org/the doi of the citation] ( do not include references in the middle of the response sentences, only include them on the end.)"
    "example : **Sources:** : - [Fertility and Sterility, 2022](https://doi.org/10.1016/j.fertnstert.2022.05.008) ... (Always keep this format as it is IMPORATANT)"
    "- Carefully review retrieved data before answering."
    "- Do not add citations that were not retrieved by retrieve_info function"
    "Ensure strict adherence to this format. Do not deviate."
    "Non-Relevant Queries:"
    "If the question is unrelated to reproductive medicine, output: Sorry, I'm not designed for this type of question."
    "For casual conversation, respond appropriately without this disclaimer. but keep the output format as it is"
    "return in at max 1000 characters"
    
    )
    }

    functions = [
        {
            "name": "retrieve_info",
            "description": "Retrieve needed information to answer questions related to reproductive medicine. (Must be used for each question)",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question requiring information to answer it.",
                    },
                },
                "required": ["question"],
            },
        }
    ]

    messages = [system_message]+ chat_history
    print(messages)

    messages.append({"role": "user", "content": prompt})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions,
            function_call="auto",
            stream= True
        )

        full_response = ""
        assistant_message = None
        function_call = {"name": None, "arguments": ""}

        async for chunk in response:
            delta = chunk.choices[0].delta

            if delta.function_call:
                if delta.function_call.name:
                    function_call["name"] = delta.function_call.name
                if delta.function_call.arguments:
                    function_call["arguments"] += delta.function_call.arguments
            elif delta.content:
                if assistant_message is None:
                    assistant_message = {"role": "assistant", "content": ""}
                assistant_message["content"] += delta.content
                full_response += delta.content
                yield delta.content
        print(full_response)
 
        if function_call["name"]:

            try:
                function_args = json.loads(function_call["arguments"])
            except json.JSONDecodeError as e:
                print(f"Error parsing function arguments: {e}")
                function_args = {}

       
            if function_call["name"] == "retrieve_info":

                function_response = retrieve_info(
                    question=function_args.get("question")
                )
              
  
                messages.append({"role": "function", "name": function_call["name"], "content": function_response})

            second_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )

    
            full_response = ""
            async for chunk in second_response:
                if token := chunk.choices[0].delta.content or "":
                    content_chunk = token
                    full_response += content_chunk
                    yield content_chunk
            print(full_response)
            
    except Exception as e:
        print(f"An error occurred: {e}")
        yield  {
            "response": f"Sorry an Error has occured, please try again later!"
        }

