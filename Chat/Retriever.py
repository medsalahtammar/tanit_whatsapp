from neo4j_graphrag.retrievers import VectorCypherRetriever
import neo4j
import os
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings



def hybridCypherRetriever(query_text):
    
    retrieval_query = """
// Case 1: Embedding linked to SectionPart
OPTIONAL MATCH (node)<-[:HAS_EMBEDDING]-(section_part:SectionPart)
OPTIONAL MATCH (section_part)-[:HAS_ENTITY]->(section_entity:Entity)

// Previous and next SectionParts based on sequence
OPTIONAL MATCH (prev_section_part:SectionPart {authors: section_part.authors})
  WHERE prev_section_part.sequence = section_part.sequence - 1
OPTIONAL MATCH (next_section_part:SectionPart {authors: section_part.authors})
  WHERE next_section_part.sequence = section_part.sequence + 1

// Case 2: Embedding linked to Entity
OPTIONAL MATCH (node)<-[:HAS_EMBEDDING]-(entity:Entity)
OPTIONAL MATCH (entity)-[rel]->(related_entity:Entity)

// Aggregate entities and relationships
WITH 
  section_part,
  prev_section_part,
  next_section_part,
  entity,
  collect({
    name: section_entity.name,
    cui: section_entity.cui,
    semantic_type: section_entity.semantic_type,
    definitions: [key IN keys(section_entity) WHERE key STARTS WITH "definition_" AND section_entity[key] IS NOT NULL | section_entity[key]],
    relationship: "HAS_ENTITY"
  }) AS section_entities,
  collect({
    name: related_entity.name,
    cui: related_entity.cui,
    semantic_type: related_entity.semantic_type,
    definitions: [key IN keys(related_entity) WHERE key STARTS WITH "definition_" AND related_entity[key] IS NOT NULL | related_entity[key]],
    relationship: type(rel)
  }) AS related_entities

// Return clean results
RETURN
CASE 
  WHEN section_part IS NOT NULL THEN {
    section_part: {
      starting_id : ID(section_part),
      text: section_part.text,
      title: section_part.title,
      doi: section_part.doi,
      sequence: section_part.sequence,
      entities: [entity IN section_entities WHERE entity.name IS NOT NULL]
    },
    previous_section_part: CASE 
      WHEN prev_section_part IS NOT NULL THEN {
        text: prev_section_part.text,
        doi: prev_section_part.doi,
        sequence: prev_section_part.sequence
      }
      ELSE NULL
    END,
    next_section_part: CASE 
      WHEN next_section_part IS NOT NULL THEN {
        text: next_section_part.text,
        doi: next_section_part.doi,
        sequence: next_section_part.sequence
      }
      ELSE NULL
    END
  }
  ELSE NULL
END AS section_part_details,

CASE 
  WHEN entity IS NOT NULL THEN {
    entity: {
      starting_id : ID(entity),
      name: entity.name,
      cui: entity.cui,
      semantic_type: entity.semantic_type,
      definitions: [key IN keys(entity) WHERE key STARTS WITH "definition_" AND entity[key] IS NOT NULL | entity[key]],
      related_entities: [rel IN related_entities WHERE rel.name IS NOT NULL]
    }
  }
  ELSE NULL
END AS entity_details
"""

    URI = os.getenv("NEO4J_URL_GERMANY")
    AUTH = (os.getenv("NEO4J_USERNAME_GERMANY"), os.getenv("NEO4J_PASSWORD_GERMANY"))
    driver = neo4j.GraphDatabase.driver(URI, auth=AUTH)
    embedder = OpenAIEmbeddings(model="text-embedding-3-large")
    retriever = VectorCypherRetriever(
        driver=driver,
        index_name="embedding_vector",
        retrieval_query=retrieval_query,
        embedder=embedder
    )

    results = retriever.search(query_text=query_text, top_k=7)
    response=""
    for result in results:
        key, value = result
        if key == "items":
            for item in value:
                response = response + item.content
    return response



