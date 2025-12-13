import React, { useState } from 'react';
import { Music, Droplet, Search, Sparkles, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';
import ProductCard from '../components/product/ProductCard';

interface MoodInfo {
    type: string;
    detected: string;
    style: string;
    mood: string;
    colors: string[];
    description: string;
}

interface ProductResponse {
    id: number;
    name: string;
    description: string;
    price: number;
    category: string;
    image_url: string;
    stock_quantity: number;
    in_stock?: boolean;
}

interface MoodSearchResult {
    status: string;
    mood_info?: MoodInfo;
    message?: string;
    products: ProductResponse[];
}

const PERFUME_EXAMPLES = [
    "플로럴", "로즈", "자스민", "시트러스", "레몬",
    "우디", "샌달우드", "오리엔탈", "앰버",
    "아쿠아", "그린", "파우더리", "스파이시"
];

const MUSIC_EXAMPLES = [
    "클래식", "재즈", "팝", "케이팝",
    "락", "펑크", "힙합", "알앤비",
    "일렉트로닉", "하우스", "인디", "어쿠스틱", "발라드"
];

export default function MoodSearch() {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState<'perfume' | 'music'>('perfume');
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<ProductResponse[]>([]);
    const [moodInfo, setMoodInfo] = useState<MoodInfo | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState('');

    const handleSearch = async (searchQuery?: string) => {
        const finalQuery = searchQuery || query;
        if (!finalQuery.trim()) return;

        setIsLoading(true);
        setMessage('');
        setResults([]);
        setMoodInfo(null);

        const formData = new FormData();
        formData.append('query', finalQuery);
        formData.append('limit', '12');

        try {
            const response = await client.post<MoodSearchResult>(
                '/search/mood-search',
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );

            if (response.data.status === 'NO_MOOD_DETECTED') {
                setMessage(response.data.message || '무드를 감지할 수 없습니다.');
            } else {
                setResults(response.data.products || []);
                setMoodInfo(response.data.mood_info || null);
            }
        } catch (error) {
            console.error('Mood search failed:', error);
            setMessage('검색 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleExampleClick = (example: string) => {
        setQuery(example);
        handleSearch(example);
    };

    return (
        <div className="max-w-7xl mx-auto p-6 space-y-8 pb-24 min-h-screen bg-white dark:bg-black text-gray-900 dark:text-white">
            {/* 헤더 */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => navigate('/')}
                    className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                    <ArrowLeft className="w-6 h-6 text-gray-500 dark:text-gray-400" />
                </button>
                <h1 className="text-3xl font-bold flex items-center gap-2">
                    <Sparkles className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                    무드 기반 패션 검색
                </h1>
            </div>

            <p className="text-gray-600 dark:text-gray-400">
                좋아하는 향수나 음악에 어울리는 스타일을 추천해드립니다
            </p>

            {/* 탭 */}
            <div className="flex gap-4 border-b border-gray-200 dark:border-gray-800">
                <button
                    onClick={() => setActiveTab('perfume')}
                    className={`flex items-center gap-2 px-6 py-3 font-medium transition-all ${
                        activeTab === 'perfume'
                            ? 'text-purple-600 dark:text-purple-400 border-b-2 border-purple-600'
                            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}
                >
                    <Droplet className="w-5 h-5" />
                    향수 노트
                </button>
                <button
                    onClick={() => setActiveTab('music')}
                    className={`flex items-center gap-2 px-6 py-3 font-medium transition-all ${
                        activeTab === 'music'
                            ? 'text-purple-600 dark:text-purple-400 border-b-2 border-purple-600'
                            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}
                >
                    <Music className="w-5 h-5" />
                    음악 장르
                </button>
            </div>

            {/* 검색창 */}
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow-lg p-6 border border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-3">
                    <Search className="w-6 h-6 text-gray-400" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                        placeholder={
                            activeTab === 'perfume'
                                ? '예: 플로럴, 우디, 시트러스...'
                                : '예: 재즈, 힙합, 클래식...'
                        }
                        className="flex-1 text-xl border-none focus:ring-0 outline-none bg-transparent"
                    />
                    <button
                        onClick={() => handleSearch()}
                        disabled={isLoading}
                        className="px-8 py-3 bg-purple-600 text-white rounded-xl font-bold hover:bg-purple-700 transition-all active:scale-95 disabled:opacity-50"
                    >
                        검색
                    </button>
                </div>

                {/* 예시 버튼 */}
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">빠른 검색:</p>
                    <div className="flex flex-wrap gap-2">
                        {(activeTab === 'perfume' ? PERFUME_EXAMPLES : MUSIC_EXAMPLES).map((example) => (
                            <button
                                key={example}
                                onClick={() => handleExampleClick(example)}
                                className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-purple-100 dark:hover:bg-purple-900/30 text-sm rounded-lg transition-colors"
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* 로딩 */}
            {isLoading && (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-600 border-t-transparent"></div>
                </div>
            )}

            {/* 메시지 */}
            {message && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-yellow-800 dark:text-yellow-200">
                    {message}
                </div>
            )}

            {/* 무드 정보 */}
            {moodInfo && (
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30 rounded-xl p-6 border border-purple-100 dark:border-purple-800">
                    <h2 className="text-2xl font-bold mb-3">{moodInfo.detected}</h2>
                    <p className="text-gray-700 dark:text-gray-300 mb-4">{moodInfo.description}</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">스타일</p>
                            <p className="font-medium">{moodInfo.style}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 dark:text-gray-400">무드</p>
                            <p className="font-medium">{moodInfo.mood}</p>
                        </div>
                        <div className="col-span-2">
                            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">추천 컬러</p>
                            <div className="flex flex-wrap gap-2">
                                {moodInfo.colors.map((color, idx) => (
                                    <span key={idx} className="px-3 py-1 bg-white dark:bg-gray-800 rounded-full text-sm">
                                        {color}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 상품 결과 */}
            {results.length > 0 && (
                <div>
                    <h3 className="text-xl font-bold mb-4">
                        추천 상품 ({results.length}개)
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                        {results.map((product) => (
                            <ProductCard key={product.id} product={product} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
