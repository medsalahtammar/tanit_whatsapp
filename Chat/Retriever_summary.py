from neo4j_graphrag.retrievers import VectorCypherRetriever
import neo4j
import os
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.types import RetrieverResultItem

def result_formatter(record: neo4j.Record) -> RetrieverResultItem:
    section_part_details = record.get("section_part_details")
    entity_details = record.get("entity_details")
    cluster_details = record.get("cluster_details")
    content = ""
    metadata = {}

    if section_part_details:
        section_part = section_part_details.get("section_part", {})
        content += "### Section Details\n"
        content += f"- **Title**: {section_part.get('title')}\n"
        content += f"- **Text**: {section_part.get('text')}\n"
        content += f"- **DOI**: {section_part.get('doi')}\n"
        content += f"- **Sequence**: {section_part.get('sequence')}\n"
        content += f"- **Cluster Summary**: {section_part.get('summary')}\n"

        prev_section_part = section_part_details.get("previous_section_part")
        if prev_section_part:
            content += "### Previous Section\n"
            content += f"- **Text**: {prev_section_part.get('text')}\n"
            content += f"- **DOI**: {prev_section_part.get('doi')}\n"
            content += f"- **Sequence**: {prev_section_part.get('sequence')}\n"

        next_section_part = section_part_details.get("next_section_part")
        if next_section_part:
            content += "### Next Section\n"
            content += f"- **Text**: {next_section_part.get('text')}\n"
            content += f"- **DOI**: {next_section_part.get('doi')}\n"
            content += f"- **Sequence**: {next_section_part.get('sequence')}\n"

        if section_part.get("entities"):
            content += "### Entities in Section\n"
            for entity in section_part.get("entities", []):
                content += f"- **Entity Name**: {entity.get('name')}\n"
                content += f"  - **CUI**: {entity.get('cui')}\n"
                content += f"  - **Semantic Type**: {entity.get('semantic_type')}\n"
                if entity.get("definitions"):
                    content += "  - **Definitions**:\n"
                    for definition in entity.get("definitions", []):
                        content += f"    - {definition}\n"

        metadata.update({
            "section_part_id": section_part.get("starting_id"),
            "title": section_part.get("title"),
            "doi": section_part.get("doi"),
        })

    if entity_details:
        entity = entity_details.get("entity", {})
        content += "### Entity Details\n"
        content += f"- **Name**: {entity.get('name')}\n"
        content += f"- **CUI**: {entity.get('cui')}\n"
        content += f"- **Semantic Type**: {entity.get('semantic_type')}\n"

        if entity.get("definitions"):
            content += "- **Definitions**:\n"
            for definition in entity.get("definitions", []):
                content += f"  - {definition}\n"

        if entity.get("related_entities"):
            content += "- **Related Entities**:\n"
            for rel in entity.get("related_entities", []):
                content += f"  - **Name**: {rel.get('name')}\n"
                content += f"    - **CUI**: {rel.get('cui')}\n"
                content += f"    - **Relationship**: {rel.get('relationship')}\n"

        metadata.update({
            "entity_id": entity.get("starting_id"),
            "name": entity.get("name"),
            "cui": entity.get("cui"),
        })
    if cluster_details:
        cluster = cluster_details.get("cluster", {})
        content += "### Cluster Details\n"
        content += f"- **ID**: {cluster.get('id')}\n"
        content += f"- **Summary**: {cluster.get('summary')}\n"

        metadata.update({
            "cluster_id": cluster.get("starting_id"),
            "summary": cluster.get("summary"),
        })

    if not content:
        content = "No results found."

    return RetrieverResultItem(
        content=content,
        metadata=metadata
    )

def hybridCypherRetriever(query_text):
    
    retrieval_query = """
// Case 1: Embedding linked to SectionPart
OPTIONAL MATCH (node)<-[:HAS_EMBEDDING]-(section_part:SectionPart)
OPTIONAL MATCH (section_part)-[:HAS_ENTITY]->(section_entity:Entity)
OPTIONAL MATCH (section_part)-[:PART_OF_CLUSTER]->(related_cluster:Cluster)

// Previous and next SectionParts based on sequence
OPTIONAL MATCH (prev_section_part:SectionPart {authors: section_part.authors})
  WHERE prev_section_part.sequence = section_part.sequence - 1
OPTIONAL MATCH (next_section_part:SectionPart {authors: section_part.authors})
  WHERE next_section_part.sequence = section_part.sequence + 1

// Case 2: Embedding linked to Entity
OPTIONAL MATCH (node)<-[:HAS_EMBEDDING]-(entity:Entity)
OPTIONAL MATCH (entity)-[rel]->(related_entity:Entity)

// Case 3: Embedding linked to Cluster
OPTIONAL MATCH (node)<-[:HAS_EMBEDDING]-(cluster:Cluster)

// Aggregate entities and relationships
WITH 
  section_part,
  prev_section_part,
  next_section_part,
  entity,
  related_cluster,
  cluster,
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
      entities: [entity IN section_entities WHERE entity.name IS NOT NULL],
      summary: related_cluster.summary
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
END AS entity_details,

CASE 
  WHEN cluster IS NOT NULL THEN {
    cluster: {
      starting_id : ID(cluster),
      id: cluster.id,
      summary: cluster.summary
    }
  }
  ELSE NULL
END AS cluster_details
"""

    URI = os.getenv("NEO4J_URL_EASTUS")
    AUTH = (os.getenv("NEO4J_USERNAME_EASTUS"), os.getenv("NEO4J_PASSWORD_EASTUS"))
    driver = neo4j.GraphDatabase.driver(URI, auth=AUTH)
    embedder = OpenAIEmbeddings(model="text-embedding-3-large")
    retriever = VectorCypherRetriever(
        driver=driver,
        index_name="embedding_vector",
        retrieval_query=retrieval_query,
        embedder=embedder,
        result_formatter=result_formatter
    )

    result = retriever.search(query_text=query_text, top_k=3)
    try:
        contents = [item.content for item in result.items]
        
        formatted_results = ""

        for i, content in enumerate(contents, start=1):
            formatted_results += f"--- Similar Node {i} ---\n"
            formatted_results += content + "\n\n"
        print(formatted_results)
    except AttributeError:
        print("The 'result' object does not have an 'items' attribute.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return formatted_results




