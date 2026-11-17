import unittest
from football.player_values import identity_matches, assign_values, squad_values, teams_from_page


class PlayerValuesTest(unittest.TestCase):
    def setUp(self):
        self.player={'code':1,'first_name':'David','second_name':'Raya Martín','web_name':'Raya','birth_date':'1995-09-15'}
        self.record={'sourceId':562727,'name':'David Raya','birthDate':'1995-09-15','amount':23534518,'currency':'EUR','fetchedAt':'old'}

    def test_name_and_birth_must_both_match(self):
        self.assertTrue(identity_matches(self.player,self.record))
        self.assertFalse(identity_matches(self.player,{**self.record,'birthDate':'1995-09-16'}))
        self.assertFalse(identity_matches(self.player,{**self.record,'name':'David Silva'}))

    def test_ambiguous_ids_are_not_guessed(self):
        self.assertEqual(assign_values([self.player],[self.record,{**self.record,'sourceId':9}],{}),{})

    def test_failure_retains_timestamp_but_not_reused_player_code(self):
        self.assertEqual(assign_values([self.player],[],{'1':self.record})['1']['fetchedAt'],'old')
        self.assertEqual(assign_values([{**self.player,'birth_date':'1999-01-01'}],[],{'1':self.record}),{})

    def test_squad_identity_and_null_valuations(self):
        member={'id':562727,'name':'David Raya','dateOfBirth':'1995-09-15','transferValue':23534518}
        page={'fallback':{'team-9825':{'details':{'id':9825,'name':'Arsenal'},'squad':{'squad':[{'title':'keepers','members':[member,{**member,'id':2,'transferValue':None}]}]}}}}
        rows=squad_values(page,9825,'now')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['currency'],'EUR');self.assertIsNone(rows[0]['asOf'])
        with self.assertRaises(ValueError):squad_values(page,999,'now')

    def test_league_identity_and_source_url_allowlist(self):
        page={'details':{'id':47},'table':[{'all':[{'id':9825,'name':'Arsenal','pageUrl':'/teams/9825/overview/arsenal'},{'id':9,'pageUrl':'https://evil.test/'}]}]}
        self.assertEqual(len(teams_from_page(page,47)),1)
        with self.assertRaises(ValueError):teams_from_page(page,87)
