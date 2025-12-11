import os
import pytest
from src.rag import rag

class TestRag:
    def test_delete_file(self):
        local_file = "/tmp/test.txt"
        with open(local_file, 'w') as f:
            pass
        assert os.path.isfile(local_file)
        
        rag.delete_file(local_file)        
        assert not os.path.isfile(local_file)

    def test_country_adjectives_map(self):
        country_adj_map = rag.get_country_adjectives_map()
        assert len(country_adj_map) > 0
        assert country_adj_map["emilia"] == "italy"

    def test_country_params(self):
        country_list = rag.create_country_params()
        assert country_list is not None and len(country_list) > 0
        assert "Abu Dhabi".lower() in country_list

    def test_denonyms(self):
        txt = "This is Japanese car"
        demonym_list = rag.extract_countries_using_demonyms(txt)
        
        assert demonym_list is not None
        assert len(demonym_list) > 0
        assert "Japan".lower() in demonym_list

    def test_domain_entities(self):
        txt = "2019 Sakhir Grand Prix"
        domain_list = rag.extract_domain_entities(txt)
        
        assert domain_list is not None
        assert len(domain_list) > 0
        assert "Sakhir".lower() in domain_list

    def test_place_extraction(self):
        txt = "2019 Sakhir Grand Prix"
        result = rag.extract_place_from_text(txt)

        assert isinstance(result, str)
        assert result == "Bahrain".lower()

    def test_car_num_extraction(self):
        txt = "infringement of Car 30 in 2024 abu dhabi GP"
        result = rag.extract_car_num_from_txt(txt)
        
        assert isinstance(result, list)
        assert result[0] == "30"

    def test_metadata_extraction(self):
        txt = "Is the infringement of Car 30 in 2024 abu dhabi Grand Prix fair"
        result = rag.parse_metadata_from_text(txt)
        
        assert isinstance(result, dict)
        assert result["year"] == "2024"
        assert result["location"] == "abu dhabi"
        assert result["car_num"] == "30"

    def test_file_interesting_test(self):
        filename = "Infringement of Car 30 in 2024 abu dhabi GP.pdf"
        result = rag.is_file_interesting(filename)
        assert isinstance(result, bool)
        assert result == True

        filename = "Observation abou Car 15 in 2019 Austria Grand Prix.pdf"
        result = rag.is_file_interesting(filename)
        assert isinstance(result, bool)
        assert result == False

    def test_url_extraction(self):
        text = "this is test https://www.fia.com/system/files/decision-document/2025_abu_dhabi_grand_prix.pdf"
        text, filename, download_loc = rag.extract_url_and_filename(text, False)

        assert text == "this is test"
        assert filename == "2025_abu_dhabi_grand_prix"
        assert download_loc == "/tmp/2025_abu_dhabi_grand_prix.pdf"

    def test_download_url(self):
        test_url = "https://www.fia.com/system/files/decision-document/2025_abu_dhabi_grand_prix_-_infringement_-_car_18_-_more_than_one_change_of_direction.pdf"

        local_file = "/tmp/temp.pdf"
        rag.download_file(test_url, local_file)
        assert os.path.isfile(local_file)
        rag.delete_file(local_file)

    def test_chunking(self):
        ret_str, err_code = rag.create_chunks(10)
        assert err_code == rag.ERROR_CODE_SUCCESS

    def test_find_embed_files(self):
        filepath_list, file_name_list = rag.find_embed_files(rag.DECISION_JSON_DIR)
        assert len(filepath_list)

    def test_embeddings(self):
        ret_str, err_code = rag.create_embeddings(10)
        assert err_code == rag.ERROR_CODE_SUCCESS

    def test_store(self):
        ret_str, err_code = rag.store_embeddings(True)
        assert err_code == rag.ERROR_CODE_SUCCESS
    
    def test_query(self):
        query = "Is the Car 30 infringement in 2024 Abu Dhabi Grand Prix a fair penalty?"
        ret_str, err_code = rag.query(query, "gemini-default")
        assert err_code == rag.HTTP_CODE_GENERIC_SUCCESS
