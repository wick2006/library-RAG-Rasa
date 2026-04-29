from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "kewei2006"

def get_books_by_topic(topic_name):
    print(f"-> 正在 Neo4j 中检索主题: {topic_name}")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    # Cypher 查询：查找包含该主题的书籍，按评分降序，最多取 3 本
# 同时匹配 Topic 和 Category，只要任意一个包含关键词即可
    cypher_query = """
    MATCH (b:Book)-[:COVERS_TOPIC|BELONGS_TO]->(node)
    WHERE node.name CONTAINS $topic
    RETURN DISTINCT b.title AS title, b.summary AS summary, b.rating AS rating
    ORDER BY b.rating DESC
    LIMIT 3

    """
    
    results = []
    with driver.session() as session:
        records = session.run(cypher_query, topic=topic_name)
        for record in records:
            results.append({
                "书名": record["title"],
                "评分": record["rating"],
                "简介": record["summary"]
            })
            
    driver.close()
    return results

def get_author_profile(author_name):
    print(f"-> 正在 Neo4j 中检索作者: {author_name}")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    # 核心 Cypher：同时获取作者基本信息、其著作，以及与其他作者的关联
    cypher_query = """
    MATCH (a:Author {name: $author})
    // 该作者写的书
    OPTIONAL MATCH (b:Book)-[:WRITTEN_BY]->(a)
    // 该作者与其他作者的关系（不限方向）
    OPTIONAL MATCH (a)-[r]-(related:Author)
    
    RETURN 
        a.name AS name, 
        a.primary_field AS field, 
        a.bio AS bio,
        collect(DISTINCT b.title) AS books,
        collect(DISTINCT {relation_type: type(r), related_author: related.name}) AS connections
    """
    
    profile = None
    with driver.session() as session:
        result = session.run(cypher_query, author=author_name)
        record = result.single()
        
        if record and record["name"]:
            profile = {
                "姓名": record["name"],
                "主要领域": record["field"],
                "简介": record["bio"],
                "馆藏著作": record["books"],
                "学术/人物关联": record["connections"]
            }
            
    driver.close()
    return profile