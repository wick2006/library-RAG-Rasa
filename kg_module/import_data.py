import csv
from neo4j import GraphDatabase
import os

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "kewei2006"

# 使用 MERGE 语句确保不会创建重复节点和关系
IMPORT_CYPHER = """
MERGE (b:Book {title: $title})
SET b.rating = $rating, b.summary = $summary

MERGE (a:Author {name: $author})
MERGE (b)-[:WRITTEN_BY]->(a)

MERGE (c:Category {name: $category})
MERGE (b)-[:BELONGS_TO]->(c)

MERGE (t:Topic {name: $topic})
MERGE (b)-[:COVERS_TOPIC]->(t)
"""

def import_csv_to_neo4j(csv_file_path):
    print(f"开始读取文件: {csv_file_path}")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    success_count = 0
    with driver.session() as session:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 提取并转换数据类型
                params = {
                    "title": row["title"],
                    "author": row["author"],
                    "category": row["category"],
                    "topic": row["topic"],
                    "rating": float(row["rating"]),
                    "summary": row["summary"]
                }
                # 执行 Cypher 写入
                session.run(IMPORT_CYPHER, **params)
                print(f"已导入书籍: 《{row['title']}》")
                success_count += 1
                
    driver.close()
    print(f"\n导入完成！共成功处理 {success_count} 本书籍。")
# 1. 导入作者详细信息
IMPORT_AUTHORS_CYPHER = """
MERGE (a:Author {name: $name})
SET a.primary_field = $primary_field, a.bio = $bio
"""

# 2. 建立作者间的联系
IMPORT_AUTHOR_REL_CYPHER = """
MATCH (a1:Author {name: $source})
MATCH (a2:Author {name: $target})
MERGE (a1)-[r:RELATION_PLACEHOLDER]->(a2)
""".replace("RELATION_PLACEHOLDER", "$rel_type") # 动态替换关系类型

def import_extended_data():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        # 处理 authors.csv
        with open('kg_module/raw_data/authors.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.run(IMPORT_AUTHORS_CYPHER, name=row['name'], primary_field=row['primary_field'], bio=row['bio'])
        
        # 处理 author_relations.csv
        with open('kg_module/raw_data/author_relations.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 注意：关系类型需要动态拼装
                query = f"MATCH (a1:Author {{name: $s}}), (a2:Author {{name: $t}}) MERGE (a1)-[:{row['relation_type']}]->(a2)"
                session.run(query, s=row['source_author'], t=row['target_author'])
    driver.close()
    
if __name__ == "__main__":
    # 获取当前脚本所在目录，拼接 csv 的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "raw_data", "books.csv")
    
    import_csv_to_neo4j(csv_path)