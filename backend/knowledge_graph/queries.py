"""Cypher query templates for knowledge graph operations."""

CREATE_FILE_NODE = """
MERGE (f:File {id: $id})
SET f.path = $path,
    f.repo_id = $repo_id,
    f.language = $language,
    f.size_bytes = $size_bytes
RETURN f
"""

CREATE_FUNCTION_NODE = """
MERGE (fn:Function {id: $id})
SET fn.name = $name,
    fn.repo_id = $repo_id,
    fn.file_path = $file_path,
    fn.start_line = $start_line,
    fn.end_line = $end_line
RETURN fn
"""

CREATE_CLASS_NODE = """
MERGE (c:Class {id: $id})
SET c.name = $name,
    c.repo_id = $repo_id,
    c.file_path = $file_path,
    c.start_line = $start_line,
    c.end_line = $end_line
RETURN c
"""

CREATE_ENDPOINT_NODE = """
MERGE (e:APIEndpoint {id: $id})
SET e.name = $name,
    e.repo_id = $repo_id,
    e.file_path = $file_path,
    e.start_line = $start_line,
    e.end_line = $end_line
RETURN e
"""

# NOTE: {rel_type} is replaced via str.replace() — values are whitelisted in builder.py
CREATE_RELATIONSHIP = """
MATCH (a {id: $source_id})
MATCH (b {id: $target_id})
MERGE (a)-[r:{rel_type}]->(b)
RETURN r
"""

GET_ALL_NODES = """
MATCH (n)
WHERE n.repo_id = $repo_id
RETURN n.id AS id,
       labels(n)[0] AS type,
       coalesce(n.name, n.path, n.id) AS name,
       coalesce(n.file_path, n.path) AS file_path
"""

GET_ALL_RELATIONSHIPS = """
MATCH (a)-[r]->(b)
WHERE a.repo_id = $repo_id AND b.repo_id = $repo_id
RETURN a.id AS source, type(r) AS relationship, b.id AS target
"""

GET_FILE_DEPENDENCIES = """
MATCH (f:File {repo_id: $repo_id})-[:IMPORTS]->(dep)
RETURN f.path AS file, collect(dep.path) AS dependencies
"""

# Bounded depth (max 20 hops) to prevent OOM on large graphs
FIND_CIRCULAR_DEPS = """
MATCH path = (f:File)-[:IMPORTS*2..20]->(f)
WHERE f.repo_id = $repo_id
RETURN [n IN nodes(path) | n.path] AS cycle
LIMIT 20
"""

DELETE_REPO_GRAPH = """
MATCH (n {repo_id: $repo_id})
DETACH DELETE n
"""
