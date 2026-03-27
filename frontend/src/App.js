import "@/App.css";
import { BrowserRouter, Routes, Route, Link, useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import axios from "axios";
import { Search, TrendingUp, Skull, FileText, Menu, X, ExternalLink, Check, AlertTriangle, ChevronRight, Loader2, Clock, ArrowRight, Link as LinkIcon } from "lucide-react";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Badge } from "./components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { ScrollArea } from "./components/ui/scroll-area";
import { Separator } from "./components/ui/separator";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ============= Hype Badge Component =============
const HypeBadge = ({ score }) => {
  const getScoreStyle = (score) => {
    if (score <= 2) return "bg-emerald-50 text-emerald-800 border-emerald-300";
    if (score === 3) return "bg-amber-50 text-amber-800 border-amber-300";
    return "bg-red-50 text-red-800 border-red-300";
  };

  const getScoreLabel = (score) => {
    if (score === 1) return "Primary Source";
    if (score === 2) return "Grounded";
    if (score === 3) return "Opinion";
    if (score === 4) return "Speculation";
    return "Clickbait";
  };

  return (
    <div 
      data-testid={`hype-badge-${score}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm border font-mono text-xs ${getScoreStyle(score)}`}
    >
      <span className="font-bold">{score}</span>
      <span className="hidden sm:inline">/ {getScoreLabel(score)}</span>
    </div>
  );
};

// ============= Header Component =============
const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-zinc-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2" data-testid="logo-link">
            <div className="w-8 h-8 bg-zinc-950 rounded-sm flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-zinc-950">SignalAI</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            <Link to="/" data-testid="nav-feed">
              <Button variant="ghost" className="text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100">
                Feed
              </Button>
            </Link>
            <Link to="/predictions" data-testid="nav-predictions">
              <Button variant="ghost" className="text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100">
                <Skull className="w-4 h-4 mr-1.5" />
                Prediction Graveyard
              </Button>
            </Link>
            <Link to="/digest" data-testid="nav-digest">
              <Button variant="ghost" className="text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100">
                <FileText className="w-4 h-4 mr-1.5" />
                Daily Digest
              </Button>
            </Link>
          </nav>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-toggle"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <nav className="md:hidden py-4 border-t border-zinc-200">
            <div className="flex flex-col gap-2">
              <Link to="/" onClick={() => setMobileMenuOpen(false)} data-testid="mobile-nav-feed">
                <Button variant="ghost" className="w-full justify-start">Feed</Button>
              </Link>
              <Link to="/predictions" onClick={() => setMobileMenuOpen(false)} data-testid="mobile-nav-predictions">
                <Button variant="ghost" className="w-full justify-start">
                  <Skull className="w-4 h-4 mr-2" />
                  Prediction Graveyard
                </Button>
              </Link>
              <Link to="/digest" onClick={() => setMobileMenuOpen(false)} data-testid="mobile-nav-digest">
                <Button variant="ghost" className="w-full justify-start">
                  <FileText className="w-4 h-4 mr-2" />
                  Daily Digest
                </Button>
              </Link>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
};

// ============= Check This Component =============
const CheckThis = () => {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleCheck = async () => {
    if (!url.trim()) {
      toast.error("Please enter a URL");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await axios.post(`${API}/check-url`, { url });
      setResult(response.data);
      toast.success("Analysis complete!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to analyze URL");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-zinc-950 text-white py-12 sm:py-16">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight mb-3">
            Check This
          </h1>
          <p className="text-zinc-400 text-base sm:text-lg">
            Paste any AI article or YouTube URL. Get the truth.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <LinkIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
            <Input
              type="url"
              placeholder="https://..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCheck()}
              className="h-14 pl-12 pr-4 text-lg bg-white text-zinc-950 border-2 border-white placeholder:text-zinc-400 focus:ring-2 focus:ring-blue-500"
              data-testid="check-url-input"
            />
          </div>
          <Button 
            onClick={handleCheck} 
            disabled={loading}
            className="h-14 px-8 bg-white text-zinc-950 hover:bg-zinc-100 font-bold text-base"
            data-testid="check-url-button"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="w-5 h-5 mr-2" />
                Analyze
              </>
            )}
          </Button>
        </div>

        {/* Results */}
        {result && (
          <div className="mt-8 bg-white text-zinc-950 rounded-sm border-2 border-white overflow-hidden" data-testid="check-result">
            <div className="p-6 border-b border-zinc-200">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <Badge variant="outline" className="mb-2 text-xs">
                    {result.source_type === "youtube" ? "YouTube" : "Article"}
                  </Badge>
                  <h3 className="font-bold text-xl truncate">{result.title}</h3>
                </div>
                <HypeBadge score={result.hype_score} />
              </div>
              <p className="mt-3 text-zinc-600 italic">{result.hype_reason}</p>
            </div>

            <div className="p-6 border-b border-zinc-200 bg-zinc-50">
              <h4 className="font-bold text-sm uppercase tracking-wider text-zinc-500 mb-2">Summary</h4>
              <p className="text-zinc-800">{result.summary}</p>
            </div>

            {result.claims?.length > 0 && (
              <div className="p-6 border-b border-zinc-200">
                <h4 className="font-bold text-sm uppercase tracking-wider text-zinc-500 mb-3">
                  Claims Made ({result.claims.length})
                </h4>
                <ul className="space-y-2">
                  {result.claims.map((claim, i) => (
                    <li key={i} className="flex items-start gap-2">
                      {claim.supported ? (
                        <Check className="w-4 h-4 text-emerald-600 mt-1 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-600 mt-1 flex-shrink-0" />
                      )}
                      <span className="text-sm">{claim.claim}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.predictions?.length > 0 && (
              <div className="p-6">
                <h4 className="font-bold text-sm uppercase tracking-wider text-zinc-500 mb-3">
                  Predictions Extracted ({result.predictions.length})
                </h4>
                <ul className="space-y-3">
                  {result.predictions.map((pred, i) => (
                    <li key={i} className="p-3 bg-zinc-50 rounded-sm border border-zinc-200">
                      <p className="font-medium text-sm">{pred.claim}</p>
                      <p className="text-xs text-zinc-500 mt-1 flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        {pred.timeframe}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

// ============= Article Card Component =============
const ArticleCard = ({ article }) => {
  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return "";
    }
  };

  return (
    <article 
      className="group p-5 border-b border-zinc-200 hover:bg-zinc-50 transition-colors duration-100"
      data-testid={`article-card-${article.id}`}
    >
      <div className="flex items-start gap-4">
        <div className="hidden sm:block w-16 text-center flex-shrink-0">
          <span className="text-xs font-medium text-zinc-500">{formatDate(article.published_at)}</span>
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
              {article.source_name}
            </span>
            {article.hype_score && <HypeBadge score={article.hype_score} />}
          </div>
          
          <h3 className="font-bold text-lg text-zinc-950 group-hover:text-blue-700 transition-colors leading-tight mb-2">
            <a 
              href={article.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:underline"
              data-testid={`article-link-${article.id}`}
            >
              {article.title}
            </a>
          </h3>
          
          {article.summary && (
            <p className="text-sm text-zinc-600 line-clamp-2">{article.summary}</p>
          )}
        </div>

        <a 
          href={article.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <ExternalLink className="w-4 h-4 text-zinc-400" />
        </a>
      </div>
    </article>
  );
};

// ============= Feed Page =============
const FeedPage = () => {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchArticles();
    fetchStats();
  }, [filter]);

  const fetchArticles = async () => {
    setLoading(true);
    try {
      let params = {};
      if (filter === "green") {
        params = { hype_max: 2 };
      } else if (filter === "yellow") {
        params = { hype_min: 3, hype_max: 3 };
      } else if (filter === "red") {
        params = { hype_min: 4 };
      }
      
      const response = await axios.get(`${API}/articles`, { params });
      setArticles(response.data);
    } catch (error) {
      console.error("Error fetching articles:", error);
      toast.error("Failed to load articles");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const triggerIngestion = async () => {
    try {
      await axios.post(`${API}/ingest`);
      toast.success("News ingestion started! Check back in a minute.");
    } catch (error) {
      toast.error("Failed to start ingestion");
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <CheckThis />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main Feed */}
          <div className="flex-1">
            <div className="bg-white border border-zinc-200 rounded-sm overflow-hidden">
              <div className="p-4 border-b border-zinc-200 flex flex-wrap items-center justify-between gap-4">
                <h2 className="font-bold text-lg text-zinc-950">AI News Feed</h2>
                
                <div className="flex items-center gap-2">
                  <Tabs value={filter} onValueChange={setFilter} data-testid="hype-filter">
                    <TabsList className="bg-zinc-100">
                      <TabsTrigger value="all" className="text-xs" data-testid="filter-all">All</TabsTrigger>
                      <TabsTrigger value="green" className="text-xs" data-testid="filter-green">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5" />
                        Low Hype
                      </TabsTrigger>
                      <TabsTrigger value="yellow" className="text-xs" data-testid="filter-yellow">
                        <span className="w-2 h-2 rounded-full bg-amber-500 mr-1.5" />
                        Opinion
                      </TabsTrigger>
                      <TabsTrigger value="red" className="text-xs" data-testid="filter-red">
                        <span className="w-2 h-2 rounded-full bg-red-500 mr-1.5" />
                        High Hype
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>
              </div>

              {loading ? (
                <div className="p-12 text-center">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto text-zinc-400" />
                  <p className="mt-3 text-zinc-500">Loading articles...</p>
                </div>
              ) : articles.length === 0 ? (
                <div className="p-12 text-center">
                  <TrendingUp className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
                  <h3 className="font-bold text-lg text-zinc-950 mb-2">No articles yet</h3>
                  <p className="text-zinc-500 mb-4">Start by fetching the latest AI news</p>
                  <Button onClick={triggerIngestion} data-testid="fetch-news-button">
                    Fetch News
                  </Button>
                </div>
              ) : (
                <div data-testid="articles-list">
                  {articles.map((article) => (
                    <ArticleCard key={article.id} article={article} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <aside className="w-full lg:w-80 flex-shrink-0">
            <div className="bg-white border border-zinc-200 rounded-sm overflow-hidden sticky top-24">
              <div className="p-4 border-b border-zinc-200">
                <h3 className="font-bold text-sm uppercase tracking-wider text-zinc-500">Stats</h3>
              </div>
              
              {stats && (
                <div className="p-4 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-zinc-600">Total Articles</span>
                    <span className="font-bold text-zinc-950">{stats.articles}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-zinc-600">Predictions Tracked</span>
                    <span className="font-bold text-zinc-950">{stats.predictions}</span>
                  </div>
                  <Separator />
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-3">Hype Distribution</h4>
                    <div className="space-y-2">
                      {[1, 2, 3, 4, 5].map((score) => (
                        <div key={score} className="flex items-center gap-2">
                          <HypeBadge score={score} />
                          <div className="flex-1 h-2 bg-zinc-100 rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${score <= 2 ? 'bg-emerald-500' : score === 3 ? 'bg-amber-500' : 'bg-red-500'}`}
                              style={{ 
                                width: `${stats.articles > 0 ? (stats.hype_distribution?.[score] || 0) / stats.articles * 100 : 0}%` 
                              }}
                            />
                          </div>
                          <span className="text-xs text-zinc-500 w-6 text-right">
                            {stats.hype_distribution?.[score] || 0}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div className="p-4 border-t border-zinc-200">
                <Button 
                  onClick={triggerIngestion} 
                  variant="outline" 
                  className="w-full"
                  data-testid="refresh-news-button"
                >
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Refresh News
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

// ============= Predictions Page =============
const PredictionsPage = () => {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetchPredictions();
  }, [filter]);

  const fetchPredictions = async () => {
    setLoading(true);
    try {
      const params = filter !== "all" ? { status: filter } : {};
      const response = await axios.get(`${API}/predictions`, { params });
      setPredictions(response.data);
    } catch (error) {
      console.error("Error fetching predictions:", error);
      toast.error("Failed to load predictions");
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await axios.patch(`${API}/predictions/${id}?status=${status}`);
      toast.success("Prediction updated");
      fetchPredictions();
    } catch (error) {
      toast.error("Failed to update prediction");
    }
  };

  const getStatusBadge = (status) => {
    if (status === "true") return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300">Proved True</Badge>;
    if (status === "false") return <Badge className="bg-red-100 text-red-800 border-red-300">Proved False</Badge>;
    return <Badge className="bg-zinc-100 text-zinc-800 border-zinc-300">Pending</Badge>;
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <Header />
      
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Skull className="w-8 h-8 text-zinc-950" />
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-zinc-950">
              Prediction Graveyard
            </h1>
          </div>
          <p className="text-zinc-500">
            Tracking predictions made by AI journalists and executives. Did they come true?
          </p>
        </div>

        <Tabs value={filter} onValueChange={setFilter} className="mb-6" data-testid="prediction-filter">
          <TabsList>
            <TabsTrigger value="all" data-testid="pred-filter-all">All</TabsTrigger>
            <TabsTrigger value="pending" data-testid="pred-filter-pending">Pending</TabsTrigger>
            <TabsTrigger value="true" data-testid="pred-filter-true">Proved True</TabsTrigger>
            <TabsTrigger value="false" data-testid="pred-filter-false">Proved False</TabsTrigger>
          </TabsList>
        </Tabs>

        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-zinc-400" />
          </div>
        ) : predictions.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <Skull className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
              <h3 className="font-bold text-lg text-zinc-950 mb-2">No predictions yet</h3>
              <p className="text-zinc-500">
                Predictions will appear here as articles are analyzed
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4" data-testid="predictions-list">
            {predictions.map((pred) => (
              <Card key={pred.id} className="overflow-hidden" data-testid={`prediction-${pred.id}`}>
                <CardContent className="p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                    <div className="flex-1">
                      <p className="font-medium text-zinc-950 text-lg">{pred.claim}</p>
                      <div className="flex items-center gap-3 mt-2 text-sm text-zinc-500">
                        <span className="flex items-center">
                          <Clock className="w-4 h-4 mr-1" />
                          {pred.predicted_timeframe}
                        </span>
                        {pred.source_title && (
                          <a 
                            href={pred.source_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="hover:text-blue-600 truncate max-w-xs"
                          >
                            {pred.source_title}
                          </a>
                        )}
                      </div>
                    </div>
                    {getStatusBadge(pred.status)}
                  </div>

                  {pred.status === "pending" && (
                    <div className="flex gap-2 pt-4 border-t border-zinc-200">
                      <Button 
                        size="sm" 
                        variant="outline"
                        className="text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                        onClick={() => updateStatus(pred.id, "true")}
                        data-testid={`mark-true-${pred.id}`}
                      >
                        <Check className="w-4 h-4 mr-1" />
                        Mark True
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline"
                        className="text-red-700 border-red-300 hover:bg-red-50"
                        onClick={() => updateStatus(pred.id, "false")}
                        data-testid={`mark-false-${pred.id}`}
                      >
                        <X className="w-4 h-4 mr-1" />
                        Mark False
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

// ============= Daily Digest Page =============
const DigestPage = () => {
  const [digest, setDigest] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDigest();
  }, []);

  const fetchDigest = async () => {
    try {
      const response = await axios.get(`${API}/digest`);
      setDigest(response.data);
    } catch (error) {
      console.error("Error fetching digest:", error);
      toast.error("Failed to load digest");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />
      
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="text-center mb-12">
          <p className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-2">
            {digest?.date || new Date().toISOString().split('T')[0]}
          </p>
          <h1 className="text-4xl sm:text-5xl font-black tracking-tight text-zinc-950 mb-4">
            Daily Digest
          </h1>
          <p className="text-lg text-zinc-500 max-w-xl mx-auto">
            The top AI developments today, filtered for signal over noise. Only stories with hype scores of 1-2.
          </p>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-zinc-400" />
          </div>
        ) : !digest?.articles?.length ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 mx-auto text-zinc-300 mb-4" />
            <h3 className="font-bold text-lg text-zinc-950 mb-2">No digest available</h3>
            <p className="text-zinc-500">
              Check back later for today's top developments
            </p>
          </div>
        ) : (
          <div className="space-y-8" data-testid="digest-articles">
            {digest.articles.map((article, index) => (
              <article key={index} className="group" data-testid={`digest-article-${index}`}>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-5xl font-black text-zinc-200">{index + 1}</span>
                  <div>
                    <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
                      {article.source_name}
                    </span>
                    <HypeBadge score={article.hype_score} />
                  </div>
                </div>
                
                <h2 className="text-2xl font-bold text-zinc-950 mb-3 group-hover:text-blue-700 transition-colors">
                  <a href={article.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    {article.title}
                  </a>
                </h2>
                
                <p className="text-zinc-600 leading-relaxed text-lg mb-4">
                  {article.summary}
                </p>
                
                <a 
                  href={article.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
                >
                  Read full article
                  <ArrowRight className="w-4 h-4 ml-1" />
                </a>
                
                {index < digest.articles.length - 1 && (
                  <Separator className="mt-8" />
                )}
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

// ============= Home Page Wrapper =============
const HomePage = () => {
  return (
    <>
      <Header />
      <FeedPage />
    </>
  );
};

// ============= App =============
function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/predictions" element={<PredictionsPage />} />
          <Route path="/digest" element={<DigestPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
