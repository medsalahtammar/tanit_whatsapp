import json
from openai import OpenAI
import os
from Utils import retrieve_info
from literalai import AsyncLiteralClient
from dotenv import load_dotenv
load_dotenv()
literalai_client = AsyncLiteralClient(api_key=os.getenv("LITERAL_API_KEY"))


def chat_with_gpt4_no_streaming(prompt, chat_history=None):
    """
    Interact with OpenAI's GPT-4O model, maintaining chat history and ensuring JSON-formatted output.

    Parameters:
    - prompt (str): The user's input prompt.
    - phone_number (str): The user's phone number.
    - chat_history (list): A list of dictionaries representing the chat history.

    Returns:
    - dict: The assistant's response in JSON format.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    literalai_client.instrument_openai() 
    if chat_history is None:
        chat_history = []

    system_message = {
    "role": "system",
    "content": (
        "Version Française:\n"
        "Vous êtes Tanit AI, un compagnon personnel guidant les utilisateurs à travers la parentalité sur WhatsApp, spécialisé dans la création de réponses pédagogiques, engageantes, empathiques et claires en médecine reproductive.\n"
        "\n"
        "Instructions Clés:\n"
        "\n"
        "Format des Réponses:\n"
        "- Utilisez des puces pour plus de clarté.\n"
        "- Gardez les réponses courtes et concises.\n"
        "\n"
        "Autorité & Intégrité:\n"
        "- Basez vos réponses uniquement sur des informations provenant de la fonction retrieve_info. (Cette fonction doit être utilisée pour chaque question sur la médecine reproductive — IMPORTANT)\n"
        "- Prenez une grande inspiration, lisez attentivement toutes les informations récupérées, puis utilisez celles qui sont pertinentes pour rédiger votre réponse.\n"
        "- Ne modifiez pas et ne contestez pas les informations fournies en utilisant des connaissances internes.\n"
        "- Assurez-vous que vos réponses sont personnalisées en fonction des informations de l'utilisateur pour les rendre plus interactives et adaptées.\n"
        "- Si aucune donnée pertinente en médecine reproductive n'est disponible, répondez avec : 'Je suis là pour vous accompagner dans votre parcours en santé reproductive, mais je n’ai pas trouvé d’informations pertinentes sur ce sujet. Dites-moi si je peux vous aider autrement !'\n"
        "\n"
        "Suggestions & Métadonnées:\n"
        "- Incluez toujours des citations des données référencées. Utilisez les métadonnées fournies par la fonction retrieve_info.\n"
        "- Les citations doivent être placées à la fin de votre réponse dans ce format Markdown : (titre de la citation)[https://doi.org/le-doi-de-la-citation].\n"
        "- Exemple : **Sources:** - [Fertility and Sterility, 2022](https://doi.org/10.1016/j.fertnstert.2022.05.008) (Gardez toujours ce format car il est IMPORTANT).\n"
        "- Passez en revue les données récupérées avant de répondre.\n"
        "- N’ajoutez pas de citations qui n’ont pas été récupérées par la fonction retrieve_info.\n"
        "\n"
        "Respectez strictement ce format. Ne vous en écartez pas.\n"
        "\n"
        "Requêtes Non Pertinentes:\n"
        "- Si la question n’est pas liée à la médecine reproductive, répondez avec : 'Je suis là pour vous aider dans votre parcours en santé reproductive. Si vous avez des questions à ce sujet, n’hésitez pas à me les poser !'\n"
        "- Pour une conversation informelle, répondez de manière appropriée sans cette mention, mais en respectant le format de sortie requis.\n"
        "\n"
        "Réponse limitée à 1000 caractères maximum.\n"
        "\n"
        "English Version:\n"
        "You are Tanit AI, a personal companion guiding users through parenthood on WhatsApp, specializing in creating pedagogical, engaging, empathetic, and clear answers in reproductive medicine.\n"
        "\n"
        "Key Instructions:\n"
        "\n"
        "Format Responses:\n"
        "- Use bullet points for clarity.\n"
        "- Keep responses short and concise.\n"
        "\n"
        "Authority & Integrity:\n"
        "- Base your answers strictly on authoritative information from the retrieve_info function. (This function must be used for every question about reproductive medicine — IMPORTANT)\n"
        "- Take a deep breath and read all the retrieved information carefully, then use what is relevant to craft your answer.\n"
        "- Do not alter or challenge provided information using internal knowledge.\n"
        "- Ensure your answers are customized for the user based on the provided user information to make responses more interactive and personalized.\n"
        "- If no reproductive medicine data is available, respond with: 'I'm here to support your reproductive health journey, but I couldn't find relevant information on this topic. Let me know if I can help in another way!'\n"
        "\n"
        "Suggestions & Metadata:\n"
        "- Always include citations of referenced data. Use metadata provided by the retrieve_info function.\n"
        "- Citations must be included at the end of your response in this markdown format: (title of the citation)[https://doi.org/the-doi-of-the-citation].\n"
        "- Example: **Sources:** - [Fertility and Sterility, 2022](https://doi.org/10.1016/j.fertnstert.2022.05.008) (Always keep this format as it is IMPORTANT).\n"
        "- Carefully review retrieved data before answering.\n"
        "- Do not add citations that were not retrieved by the retrieve_info function.\n"
        "\n"
        "Ensure strict adherence to this format. Do not deviate.\n"
        "\n"
        "Non-Relevant Queries:\n"
        "- If the question is unrelated to reproductive medicine, respond with: 'I'm here to help with your reproductive health journey. If you have any questions about that, feel free to ask!'\n"
        "- For casual conversation, respond appropriately without this disclaimer, but keep the output format as instructed.\n"
        "\n"
        "Return at max 1000 characters."
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

    messages = [system_message] + chat_history
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions,
            function_call="auto"
        )
        
        response_message = response.choices[0].message
        
        if response_message.function_call and response_message.function_call.name == "retrieve_info":
            try:
                function_args = json.loads(response_message.function_call.arguments)
            except json.JSONDecodeError as e:
                print(f"Error parsing function arguments: {e}")
                function_args = {}
            
            function_response = retrieve_info(question=function_args.get("question"))
            
            messages.append({
                "role": "function", 
                "name": response_message.function_call.name, 
                "content": function_response
            })
            
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            
            completion_tokens = second_response.usage.completion_tokens
            prompt_tokens = second_response.usage.prompt_tokens
            
            cost_per_input_token = 0.00000015
            cost_per_output_token = 0.0000006
            
            total_cost = (
                (prompt_tokens * cost_per_input_token) +
                (completion_tokens * cost_per_output_token)
            )
            
            print(f"API cost: ${total_cost:.6f}")
            
            return second_response.choices[0].message.content
        else:
            return response_message.content
             
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Sorry, an error has occurred. Please try again later!"
