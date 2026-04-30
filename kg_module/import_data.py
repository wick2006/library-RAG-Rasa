import csv
from neo4j import GraphDatabase
import os

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "kewei2006"

# ==========================================
# Cypher 语句定义区
# ==========================================

# 导入书籍及基础关联的 Cypher
IMPORT_BOOKS_CYPHER = """
MERGE (b:Book {title: $title})
SET b.rating = $rating, b.summary = $summary

MERGE (a:Author {name: $author})
MERGE (b)-[:WRITTEN_BY]->(a)

MERGE (c:Category {name: $category})
MERGE (b)-[:BELONGS_TO]->(c)

MERGE (t:Topic {name: $topic})
MERGE (b)-[:COVERS_TOPIC]->(t)
"""

# 导入作者详细信息的 Cypher
IMPORT_AUTHORS_CYPHER = """
MERGE (a:Author {name: $name})
SET a.primary_field = $primary_field, a.bio = $bio
"""


# ==========================================
# 执行函数区
# ==========================================

def import_csv_to_neo4j(csv_file_path):
    print(f"-> 开始读取书籍基础数据: {csv_file_path}")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    success_count = 0
    with driver.session() as session:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                params = {
                    "title": row["title"].strip(),
                    "author": row["author"].strip(),
                    "category": row["category"].strip(),
                    "topic": row["topic"].strip(),
                    "rating": float(row["rating"]) if row["rating"] else 0.0,
                    "summary": row["summary"].strip()
                }
                session.run(IMPORT_BOOKS_CYPHER, **params)
                print(f"  已导入书籍: 《{row['title']}》")
                success_count += 1
                
    driver.close()
    print(f"书籍导入完成！共成功处理 {success_count} 条记录。\n")


def import_extended_data(authors_csv_path, relations_csv_path):
    print(f"-> 开始读取作者扩展数据...")
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    with driver.session() as session:
        # 1. 处理 authors.csv
        print(f"  正在导入作者档案: {authors_csv_path}")
        with open(authors_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.run(IMPORT_AUTHORS_CYPHER, 
                            name=row['name'].strip(), 
                            primary_field=row['primary_field'].strip(), 
                            bio=row['bio'].strip())
                
        # 2. 处理 author_relations.csv
        print(f"  正在构建学术脉络网络: {relations_csv_path}")
        with open(relations_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rel_type = row['relation_type'].strip().upper()
                source = row['source_author'].strip()
                target = row['target_author'].strip()
                
                # 动态拼装关系类型并执行
                query = f"""
                MATCH (a1:Author {{name: $s}})
                MATCH (a2:Author {{name: $t}})
                MERGE (a1)-[:{rel_type}]->(a2)
                """
                session.run(query, s=source, t=target)
                
    driver.close()
    print("作者扩展数据导入完成！\n")


if __name__ == "__main__":
    # 获取当前脚本所在目录的绝对路径，确保从任何地方运行都不会报路径错误
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 动态拼接所有所需 CSV 文件的绝对路径
    books_csv_path = os.path.join(current_dir, "raw_data", "books.csv")
    authors_csv_path = os.path.join(current_dir, "raw_data", "authors.csv")
    relations_csv_path = os.path.join(current_dir, "raw_data", "author_relations.csv")
    
    # 按顺序执行导入
    import_csv_to_neo4j(books_csv_path)
    import_extended_data(authors_csv_path, relations_csv_path)
    
    print("所有知识图谱数据初始化完毕！")