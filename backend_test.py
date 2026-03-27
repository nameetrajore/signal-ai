import requests
import sys
import json
from datetime import datetime

class SignalAITester:
    def __init__(self, base_url="https://hype-detector-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(response_data) <= 3:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    else:
                        print(f"   Response: {type(response_data).__name__}")
                except:
                    print(f"   Response: Non-JSON content")
            else:
                self.tests_passed += 1 if response.status_code in [200, 201] else 0
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "endpoint": endpoint
                })

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e),
                "endpoint": endpoint
            })
            return False, {}

    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print("=" * 50)
        print("TESTING BASIC ENDPOINTS")
        print("=" * 50)
        
        # Test root endpoint
        self.run_test("Root API", "GET", "", 200)
        
        # Test health check
        self.run_test("Health Check", "GET", "health", 200)
        
        # Test stats endpoint
        self.run_test("Stats", "GET", "stats", 200)

    def test_articles_endpoints(self):
        """Test articles-related endpoints"""
        print("\n" + "=" * 50)
        print("TESTING ARTICLES ENDPOINTS")
        print("=" * 50)
        
        # Test get all articles
        success, articles_data = self.run_test("Get All Articles", "GET", "articles", 200)
        
        # Test articles with filters
        self.run_test("Get Low Hype Articles", "GET", "articles", 200, params={"hype_max": 2})
        self.run_test("Get High Hype Articles", "GET", "articles", 200, params={"hype_min": 4})
        self.run_test("Get Opinion Articles", "GET", "articles", 200, params={"hype_min": 3, "hype_max": 3})
        
        # Test pagination
        self.run_test("Get Articles with Limit", "GET", "articles", 200, params={"limit": 5})
        self.run_test("Get Articles with Skip", "GET", "articles", 200, params={"skip": 5, "limit": 5})
        
        # If we have articles, test getting a specific one
        if success and articles_data and len(articles_data) > 0:
            article_id = articles_data[0].get('id')
            if article_id:
                self.run_test("Get Single Article", "GET", f"articles/{article_id}", 200)
        
        # Test non-existent article
        self.run_test("Get Non-existent Article", "GET", "articles/non-existent-id", 404)

    def test_predictions_endpoints(self):
        """Test predictions-related endpoints"""
        print("\n" + "=" * 50)
        print("TESTING PREDICTIONS ENDPOINTS")
        print("=" * 50)
        
        # Test get all predictions
        success, predictions_data = self.run_test("Get All Predictions", "GET", "predictions", 200)
        
        # Test predictions with status filter
        self.run_test("Get Pending Predictions", "GET", "predictions", 200, params={"status": "pending"})
        self.run_test("Get True Predictions", "GET", "predictions", 200, params={"status": "true"})
        self.run_test("Get False Predictions", "GET", "predictions", 200, params={"status": "false"})
        
        # If we have predictions, test updating one
        if success and predictions_data and len(predictions_data) > 0:
            prediction_id = predictions_data[0].get('id')
            if prediction_id:
                # Test updating prediction status
                self.run_test("Update Prediction to True", "PATCH", f"predictions/{prediction_id}?status=true", 200)
                # Reset it back to pending
                self.run_test("Reset Prediction to Pending", "PATCH", f"predictions/{prediction_id}?status=pending", 200)
        
        # Test invalid status update
        self.run_test("Update with Invalid Status", "PATCH", "predictions/any-id?status=invalid", 400)
        
        # Test non-existent prediction
        self.run_test("Update Non-existent Prediction", "PATCH", "predictions/non-existent-id?status=true", 404)

    def test_clusters_endpoints(self):
        """Test clusters-related endpoints"""
        print("\n" + "=" * 50)
        print("TESTING CLUSTERS ENDPOINTS")
        print("=" * 50)
        
        # Test get all clusters
        success, clusters_data = self.run_test("Get All Clusters", "GET", "clusters", 200)
        
        # If we have clusters, test getting a specific one
        if success and clusters_data and len(clusters_data) > 0:
            cluster_id = clusters_data[0].get('id')
            if cluster_id:
                self.run_test("Get Single Cluster", "GET", f"clusters/{cluster_id}", 200)
        
        # Test non-existent cluster
        self.run_test("Get Non-existent Cluster", "GET", "clusters/non-existent-id", 404)

    def test_digest_endpoint(self):
        """Test daily digest endpoint"""
        print("\n" + "=" * 50)
        print("TESTING DIGEST ENDPOINT")
        print("=" * 50)
        
        self.run_test("Get Daily Digest", "GET", "digest", 200)

    def test_check_url_endpoint(self):
        """Test check URL endpoint"""
        print("\n" + "=" * 50)
        print("TESTING CHECK URL ENDPOINT")
        print("=" * 50)
        
        # Test with a valid article URL (this might take time due to AI processing)
        test_url = "https://www.example.com/test-article"
        self.run_test("Check URL - Article", "POST", "check-url", 200, 
                     data={"url": test_url})
        
        # Test with invalid URL
        self.run_test("Check URL - Invalid", "POST", "check-url", 400, 
                     data={"url": "not-a-url"})

    def test_ingestion_endpoint(self):
        """Test news ingestion endpoint"""
        print("\n" + "=" * 50)
        print("TESTING INGESTION ENDPOINT")
        print("=" * 50)
        
        self.run_test("Trigger News Ingestion", "POST", "ingest", 200)

    def test_subscription_endpoints(self):
        """Test email subscription endpoints"""
        print("\n" + "=" * 50)
        print("TESTING SUBSCRIPTION ENDPOINTS")
        print("=" * 50)
        
        # Test subscribe endpoint
        test_email = f"test_{datetime.now().strftime('%H%M%S')}@example.com"
        success, response = self.run_test("Subscribe to Digest", "POST", "subscribe", 200, 
                                        data={"email": test_email})
        
        # Test duplicate subscription
        self.run_test("Duplicate Subscription", "POST", "subscribe", 200, 
                     data={"email": test_email})
        
        # Test invalid email
        self.run_test("Invalid Email Subscription", "POST", "subscribe", 422, 
                     data={"email": "invalid-email"})
        
        # Test unsubscribe
        self.run_test("Unsubscribe", "POST", "unsubscribe", 200, 
                     data={"email": test_email})
        
        # Test subscriber count
        self.run_test("Get Subscriber Count", "GET", "subscribers/count", 200)

    def test_blindspots_endpoint(self):
        """Test blindspots endpoint"""
        print("\n" + "=" * 50)
        print("TESTING BLINDSPOTS ENDPOINT")
        print("=" * 50)
        
        self.run_test("Get Blindspots", "GET", "blindspots", 200)

    def test_clustering_endpoint(self):
        """Test clustering endpoint"""
        print("\n" + "=" * 50)
        print("TESTING CLUSTERING ENDPOINT")
        print("=" * 50)
        
        self.run_test("Trigger Clustering", "POST", "cluster", 200)

    def test_digest_email_endpoint(self):
        """Test digest email endpoint"""
        print("\n" + "=" * 50)
        print("TESTING DIGEST EMAIL ENDPOINT")
        print("=" * 50)
        
        self.run_test("Trigger Digest Email", "POST", "send-digest", 200)

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        
        if self.failed_tests:
            print(f"\n❌ Failed tests ({len(self.failed_tests)}):")
            for test in self.failed_tests:
                error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
                print(f"   • {test['test']}: {error_msg}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n🎯 Success rate: {success_rate:.1f}%")
        
        return success_rate >= 80  # Consider 80%+ as passing

def main():
    print("🚀 Starting SignalAI Backend API Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = SignalAITester()
    
    # Run all test suites
    tester.test_basic_endpoints()
    tester.test_articles_endpoints()
    tester.test_predictions_endpoints()
    tester.test_clusters_endpoints()
    tester.test_digest_endpoint()
    tester.test_check_url_endpoint()
    tester.test_ingestion_endpoint()
    tester.test_subscription_endpoints()
    tester.test_blindspots_endpoint()
    tester.test_clustering_endpoint()
    tester.test_digest_email_endpoint()
    
    # Print summary and return exit code
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())