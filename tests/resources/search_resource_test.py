import os
import unittest
import logging
import shutil
from resources.search_resource import SearchResourceConfig, SearchResource
from retrying import retry

# Configure logging
logging.basicConfig(level=logging.INFO) 

class SearchResourceTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_search_links(self):
        config = SearchResourceConfig()

        search_resource = SearchResource(resource_id="test_search_resource", config=config)
        search_results = search_resource.get_search_links("wikipedia")    
        self.assertEqual(len(search_results), 3, "Incorrect number of default search results")

        search_results = search_resource.get_search_links("wikipedia", 2)    
        self.assertEqual(len(search_results), 2, "Incorrect number of custom search results")


    def test_search(self):
        config = SearchResourceConfig(
            search_result_count = 2
        )

        search_resource = SearchResource(resource_id="test_search_resource", config=config)
        search_results = search_resource.search("dijkstra")    
        for result in search_results:
            self.assertTrue("dijkstra" in result.lower(), "Search result does not contain query djikstra")

if __name__ == '__main__':
    unittest.main()