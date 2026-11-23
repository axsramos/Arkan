import sqlite3
import unittest
import cbor2

from backend.database import initialize_schema
from backend.library import LibraryError, allow_reimport, get_local_classification, list_comments, list_headers, read_content, register_header, remove_foreign_content, set_local_classification

class LibraryTests(unittest.TestCase):
    def test_member_removes_only_foreign_content_and_preserves_header(self):
        connection=sqlite3.connect(':memory:'); initialize_schema(connection)
        connection.execute("INSERT INTO networks VALUES ('n','g','t')")
        connection.execute("INSERT INTO members VALUES ('a','n','s1','e1','MEMBRO','ATIVO','h1','t')")
        register_header(connection,{'hash':'h','autor_id':'a','sequencia':1,'tipo':'ARTIGO','titulo':'T','criado_em':'t'})
        connection.execute("INSERT INTO publications VALUES ('h','a',1,'ARTIGO',NULL,'T','Corpo',NULL,X'01',X'02','t','PUBLICADO')")
        remove_foreign_content(connection,'local','MEMBRO','h')
        self.assertEqual(connection.execute("SELECT removed_locally FROM local_content_control WHERE content_hash='h'").fetchone()[0],1)
        self.assertEqual(connection.execute("SELECT count(*) FROM content_headers").fetchone()[0],1)
        self.assertEqual(connection.execute("SELECT count(*) FROM publications").fetchone()[0],0)
        allow_reimport(connection,'h')
        self.assertEqual(connection.execute("SELECT removed_locally FROM local_content_control WHERE content_hash='h'").fetchone()[0],0)
        self.assertTrue(list_headers(connection, 'local', 'ATIVO')[0]['proprio'] is False)
        self.assertEqual(len(list_headers(connection, 'local', 'REVOGADO')), 0)
        with self.assertRaises(LibraryError): remove_foreign_content(connection,'local','GUARDIAO','h')
        connection.close()

    def test_distinguishes_summary_from_complete_publication(self):
        connection=sqlite3.connect(':memory:'); initialize_schema(connection)
        connection.execute("INSERT INTO networks VALUES ('n','g','t')")
        connection.execute("INSERT INTO members VALUES ('a','n','s1','e1','MEMBRO','ATIVO','h1','t')")
        register_header(connection,{'hash':'h','autor_id':'a','sequencia':1,'tipo':'ARTIGO','titulo':'T','criado_em':'t'})
        summary=read_content(connection, 'local', 'ATIVO', 'h')
        self.assertFalse(summary['tem_corpo'])
        self.assertIsNone(summary['corpo'])
        connection.execute("INSERT INTO publications VALUES ('h','a',1,'ARTIGO',NULL,'T','Corpo',NULL,X'01',X'02','t','PUBLICADO')")
        complete=read_content(connection, 'local', 'ATIVO', 'h')
        self.assertTrue(complete['tem_corpo'])
        self.assertEqual(complete['corpo'], 'Corpo')
        connection.close()

    def test_lists_article_comments_and_hides_foreign_comment_from_revoked_copy(self):
        connection=sqlite3.connect(':memory:'); initialize_schema(connection)
        connection.execute("INSERT INTO networks VALUES ('n','g','t')")
        connection.execute("INSERT INTO members VALUES ('a','n','s1','e1','MEMBRO','ATIVO','h1','t')")
        connection.execute("INSERT INTO members VALUES ('local','n','s2','e2','MEMBRO','ATIVO','h2','t')")
        register_header(connection, {'hash':'article','autor_id':'a','sequencia':1,'tipo':'ARTIGO','titulo':'T','criado_em':'t'})
        register_header(connection, {'hash':'comment','autor_id':'a','sequencia':2,'tipo':'COMENTARIO','artigo_id':'article','titulo':None,'criado_em':'u'})
        connection.execute("INSERT INTO publications VALUES ('comment','a',2,'COMENTARIO','article',NULL,'Comentário',NULL,X'01',X'02','u','PUBLICADO')")

        self.assertEqual(list_comments(connection, 'local', 'ATIVO', 'article')[0]['corpo'], 'Comentário')
        headers = {item['hash']: item for item in list_headers(connection, 'local', 'ATIVO')}
        self.assertEqual(headers['article']['comentarios'], 1)
        self.assertEqual(list_comments(connection, 'local', 'REVOGADO', 'article'), [])
        connection.close()

    def test_keeps_one_category_and_free_badges_only_locally(self):
        connection=sqlite3.connect(':memory:'); initialize_schema(connection)
        connection.execute("INSERT INTO networks VALUES ('n','g','t')")
        connection.execute("INSERT INTO members VALUES ('a','n','s1','e1','MEMBRO','ATIVO','h1','t')")
        register_header(connection, {'hash':'article','autor_id':'a','sequencia':1,'tipo':'ARTIGO','titulo':'T','criado_em':'t'})

        classification = set_local_classification(connection, 'article', 'Leituras', ['Favorito', 'Para revisar'])

        self.assertEqual(classification['categoria'], 'Leituras')
        self.assertEqual(classification['badges'], ['Favorito', 'Para revisar'])
        self.assertEqual(get_local_classification(connection, 'article')['categorias_disponiveis'], ['Leituras'])
        self.assertEqual(list_headers(connection, 'local', 'ATIVO')[0]['categoria'], 'Leituras')
        self.assertEqual(list_headers(connection, 'local', 'ATIVO')[0]['badges'], ['Favorito', 'Para revisar'])
        connection.close()

    def test_uses_public_pseudonym_from_authorization_for_presentation(self):
        connection=sqlite3.connect(':memory:'); initialize_schema(connection)
        connection.execute("INSERT INTO networks VALUES ('n','g','t')")
        connection.execute("INSERT INTO members VALUES ('a','n','s1','e1','MEMBRO','ATIVO','h1','t')")
        register_header(connection, {'hash':'article','autor_id':'a','sequencia':1,'tipo':'ARTIGO','titulo':'T','criado_em':'t'})
        state = {'membros': [{'membro_id':'a', 'pseudonimo':'Aurora'}]}
        connection.execute("INSERT INTO authorization_anchors VALUES ('n',1,X'01',?,'t')", (cbor2.dumps(state, canonical=True),))

        self.assertEqual(list_headers(connection, 'local', 'ATIVO', 'n')[0]['autor_pseudonimo'], 'Aurora')
        connection.close()

    def test_reports_whether_own_article_was_exported_locally(self):
        connection=sqlite3.connect(':memory:'); initialize_schema(connection)
        connection.execute("INSERT INTO networks VALUES ('n','local','t')")
        connection.execute("INSERT INTO members VALUES ('local','n','s1','e1','MEMBRO','ATIVO','h1','t')")
        register_header(connection, {'hash':'not-exported','autor_id':'local','sequencia':1,'tipo':'ARTIGO','titulo':'Local','criado_em':'t'})
        register_header(connection, {'hash':'exported','autor_id':'local','sequencia':2,'tipo':'ARTIGO','titulo':'Enviado','criado_em':'u'})
        connection.execute("INSERT INTO export_records VALUES ('export-1','COMPLETA','u')")
        connection.execute("INSERT INTO export_items VALUES ('export-1','exported')")

        headers = {item['hash']: item for item in list_headers(connection, 'local', 'ATIVO')}

        self.assertFalse(headers['not-exported']['exportado'])
        self.assertTrue(headers['exported']['exportado'])
        self.assertTrue(headers['not-exported']['proprio'])
        connection.close()
