import React, { useState, useEffect } from "react";
import client from "@/api/client";
import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
// 세련된 아이콘들을 불러왔어! (Trash2 아이콘 추가)
import { Upload, Shirt, User, Maximize2, RefreshCw, Layers, CheckCircle, Trash2 } from "lucide-react";

// 히스토리 타입 정의
interface HistoryItem {
  id: number;
  result_image_url: string;
  category: string;
  created_at: string;
}

// 로딩 문구 리스트
const LOADING_MESSAGES = [
  "MODIFY가 고객님의 체형을 분석하고 있어요",
  "옷의 주름을 다림질하는 중...",
  "어떤 핏이 나올지 계산하고 있어요",
  "조명을 자연스럽게 맞추는 중이에요",
  "옷감을 부드럽게 만들고 있어요 ",
  "거의 다 됐어요! 핏을 확인해보세요",
  "마무리 픽셀을 다듬는 중..."
];

export default function VirtualFitting() {
    // --- [로직 유지] 상태 관리 ---
    const [humanFile, setHumanFile] = useState<File | null>(null);
    const [garmentFile, setGarmentFile] = useState<File | null>(null);
    const [resultImage, setResultImage] = useState<string | null>(null);
    
    const [category, setCategory] = useState<string>("upper_body");
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

    const [isLoading, setIsLoading] = useState(false);
    const [loadingMsgIndex, setLoadingMsgIndex] = useState(0);
    const [progress, setProgress] = useState(0);

    // --- [로직 유지] 히스토리 불러오기 ---
    const fetchHistory = async () => {
        try {
            const res = await client.get("/fitting/history");
            setHistory(res.data);
        } catch (err) {
            console.error("히스토리 불러오기 실패:", err);
        }
    };

    // --- [로직 유지] 페이지 접속 시 히스토리 로딩 ---
    useEffect(() => {
        fetchHistory();
    }, []);

    // --- [로직 유지] 로딩 애니메이션 타이머 (useEffect) ---
    useEffect(() => {
        let msgInterval: NodeJS.Timeout;
        let progressInterval: NodeJS.Timeout;

        if (isLoading) {
            setLoadingMsgIndex(0);
            setProgress(0);

            // 1. 문구 변경 (3초마다)
            msgInterval = setInterval(() => {
                setLoadingMsgIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
            }, 3000);

            // 2. 가짜 진행률 바 (0% -> 98%까지 천천히 증가)
            progressInterval = setInterval(() => {
                setProgress((prev) => {
                    if (prev >= 98) return 98; // 98%에서 멈춤
                    const increment = prev < 60 ? Math.random() * 6 : Math.random() * 3;
                    return Math.min(prev + increment, 98);
                });
            }, 500);
        }

        return () => {
          if (msgInterval) clearInterval(msgInterval);
          if (progressInterval) clearInterval(progressInterval);
        };
    }, [isLoading]);

    // --- [로직 유지] 공통 붙여넣기 핸들러 ---
    const handlePaste = (
        e: React.ClipboardEvent, 
        setFile: React.Dispatch<React.SetStateAction<File | null>>
    ) => {
        const items = e.clipboardData.items;
        for (const item of items) {
            if (item.type.indexOf('image') !== -1) {
                const blob = item.getAsFile();
                if (blob) {
                    setFile(blob);
                    e.preventDefault(); 
                    console.log("이미지 붙여넣기 성공!");
                }
                break;
            }
        }
    };

    // --- [로직 유지] 가상 피팅 실행 핸들러 ---
    const handleFitting = async () => {
        if (!humanFile || !garmentFile) return alert("이미지를 모두 올려주세요.");

        setIsLoading(true);
        setResultImage(null);
        const formData = new FormData();
        formData.append("human_img", humanFile);
        formData.append("garm_img", garmentFile);
        formData.append("category", category); 

        try {
            const response = await client.post("fitting/generate", formData, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 300000, 
            });
            setResultImage(response.data.image_url);
            fetchHistory(); 
        } catch (error) {
            console.error(error);
            alert("가상 피팅에 실패했습니다. 다시 시도해주세요.");
        } finally {
            setIsLoading(false);
        }
    };

    // --- [추가 로직] 히스토리 삭제 핸들러 ---
    const handleDelete = async (id: number) => {
        if (!confirm("이 피팅 기록을 정말 삭제할까요?")) return;

        try {
            // 백엔드 서버에 삭제 요청을 보내
            await client.delete(`/fitting/history/${id}`);
            
            // 성공하면 현재 화면(상태)에서 해당 아이템을 즉시 제거해줘
            setHistory((prev) => prev.filter((item) => item.id !== id));
        } catch (error) {
            console.error("삭제 실패:", error);
            alert("삭제 중 오류가 발생했습니다.");
        }
    };

    return (
        <div className="min-h-screen bg-white py-12 px-4 sm:px-6 lg:px-8 font-sans text-slate-900">
            <div className="max-w-5xl mx-auto">
                {/* 헤더 섹션: 미니멀한 텍스트 */}
                <header className="text-center mb-12">
                    <h1 className="text-4xl font-black tracking-tight mb-3">MODIFY Virtual Fitting</h1>
                    <p className="text-slate-500 font-medium">당신만의 완벽한 스타일을 AI로 확인해보세요.</p>
                </header>
                
                {/* [로직 유지] 카테고리 선택 버튼: 깔끔한 칩 스타일로 변경 */}
                <div className="flex justify-center gap-3 mb-12">
                    {[
                        { label: '상의', value: 'upper_body' },
                        { label: '하의', value: 'lower_body' },
                        { label: '아우터/원피스', value: 'dresses' },
                    ].map((item) => (
                    <button
                        key={item.value}
                        onClick={() => setCategory(item.value)}
                        className={`px-8 py-2.5 rounded-full text-sm font-bold transition-all border ${
                        category === item.value
                            ? 'bg-slate-900 text-white border-slate-900 shadow-lg'
                            : 'bg-white text-slate-400 border-slate-200 hover:border-slate-400'
                        }`}
                    >
                        {item.label}
                    </button>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
                    {/* 1. 내 사진 업로드 */}
                    <div 
                        tabIndex={0}
                        onPaste={(e) => handlePaste(e, setHumanFile)}
                        className="relative group border border-slate-200 rounded-3xl p-6 flex flex-col items-center justify-center min-h-[400px] 
                                   bg-slate-50/50 hover:bg-white hover:border-indigo-500 hover:shadow-2xl hover:shadow-indigo-100 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        {humanFile ? (
                            <div className="relative w-full h-full flex flex-col items-center">
                                <img src={URL.createObjectURL(humanFile)} className="h-64 object-contain rounded-2xl mb-4" />
                                <button onClick={() => setHumanFile(null)} className="text-xs font-bold text-red-500 underline decoration-2 underline-offset-4">다시 선택</button>
                            </div>
                        ) : (
                            <div className="text-center">
                                <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm mb-4 mx-auto group-hover:scale-110 transition-transform">
                                    <User className="text-slate-400 group-hover:text-indigo-500" size={32} />
                                </div>
                                <p className="font-bold text-slate-800">내 전신 사진</p>
                                <p className="text-xs text-slate-400 mt-2 mb-6">전신이 선명하게 나온 사진</p>
                                <label className="cursor-pointer bg-slate-900 text-white px-5 py-2 rounded-xl text-xs font-bold hover:bg-indigo-600 transition-colors">
                                    파일 선택
                                    <input type="file" accept="image/*" onChange={(e) => setHumanFile(e.target.files?.[0] || null)} className="hidden" />
                                </label>
                                <p className="text-[10px] mt-4 text-indigo-500 font-bold bg-indigo-50 px-3 py-1 rounded-full">클릭 후 Ctrl+V 가능</p>
                            </div>
                        )}
                    </div>

                    {/* 2. 옷 사진 업로드 */}
                    <div 
                        tabIndex={0}
                        onPaste={(e) => handlePaste(e, setGarmentFile)}
                        className="relative group border border-slate-200 rounded-3xl p-6 flex flex-col items-center justify-center min-h-[400px] 
                                   bg-slate-50/50 hover:bg-white hover:border-indigo-500 hover:shadow-2xl hover:shadow-indigo-100 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        {garmentFile ? (
                            <div className="relative w-full h-full flex flex-col items-center">
                                <img src={URL.createObjectURL(garmentFile)} className="h-64 object-contain rounded-2xl mb-4" />
                                <button onClick={() => setGarmentFile(null)} className="text-xs font-bold text-red-500 underline decoration-2 underline-offset-4">다시 선택</button>
                            </div>
                        ) : (
                            <div className="text-center">
                                <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-sm mb-4 mx-auto group-hover:scale-110 transition-transform">
                                    <Shirt className="text-slate-400 group-hover:text-indigo-500" size={32} />
                                </div>
                                <p className="font-bold text-slate-800">피팅할 의상</p>
                                <p className="text-xs text-slate-400 mt-2 mb-6">{category === 'upper_body' ? '상의' : category === 'lower_body' ? '하의' : '드레스'} 사진</p>
                                <label className="cursor-pointer bg-slate-900 text-white px-5 py-2 rounded-xl text-xs font-bold hover:bg-indigo-600 transition-colors">
                                    파일 선택
                                    <input type="file" accept="image/*" onChange={(e) => setGarmentFile(e.target.files?.[0] || null)} className="hidden" />
                                </label>
                                <p className="text-[10px] mt-4 text-indigo-500 font-bold bg-indigo-50 px-3 py-1 rounded-full">클릭 후 Ctrl+V 가능</p>
                            </div>
                        )}
                    </div>

                    {/* 3. 결과 화면 */}
                    <div className="border border-slate-200 bg-slate-50 rounded-3xl p-6 flex flex-col items-center justify-center min-h-[400px] relative overflow-hidden">
                        {isLoading ? (
                            <div className="w-full h-full flex flex-col items-center justify-center bg-white/80 backdrop-blur-md absolute inset-0 z-20 transition-all">
                                <div className="mb-8 relative">
                                    <div className="w-20 h-20 border-2 border-indigo-100 border-t-indigo-600 rounded-full animate-spin"></div>
                                    <div className="absolute inset-0 flex items-center justify-center text-indigo-600">
                                        <Layers size={24} className="animate-pulse" />
                                    </div>
                                </div>
                                <p className="text-lg font-black text-slate-800 mb-2 px-6 text-center h-14">{LOADING_MESSAGES[loadingMsgIndex]}</p>
                                <p className="text-xs text-slate-400 mb-8">최대 1분 정도 소요됩니다.</p>
                                <div className="w-48 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-indigo-600 transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
                                </div>
                                <p className="text-xs text-indigo-600 font-black mt-3">{Math.round(progress)}%</p>
                            </div>
                        ) : resultImage && humanFile ? (
                            <div className="w-full h-full flex flex-col items-center relative group">
                                <div className="w-full h-[320px] rounded-2xl overflow-hidden border border-slate-100 shadow-lg">
                                    <ReactCompareSlider
                                        itemOne={<ReactCompareSliderImage src={URL.createObjectURL(humanFile)} alt="Original" />}
                                        itemTwo={<ReactCompareSliderImage src={resultImage} alt="Result" />}
                                        handle={
                                            <div className="w-1 h-full bg-white relative flex items-center justify-center">
                                                <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center shadow-xl border border-slate-100">
                                                    <div className="flex gap-0.5">
                                                        <div className="w-0.5 h-3 bg-slate-300"></div>
                                                        <div className="w-0.5 h-3 bg-slate-300"></div>
                                                    </div>
                                                </div>
                                            </div>
                                        }
                                    />
                                </div>
                                <p className="mt-4 text-[10px] text-slate-400 font-bold uppercase tracking-widest">Slider to Compare</p>
                                <button onClick={() => setSelectedImage(resultImage)} className="absolute top-4 right-4 bg-white/90 p-2 rounded-full shadow-lg hover:bg-white transition-all opacity-0 group-hover:opacity-100">
                                    <Maximize2 size={16} className="text-slate-700" />
                                </button>
                            </div>
                        ) : (
                            <div className="text-center">
                                <Maximize2 size={48} className="text-slate-200 mb-4 mx-auto" strokeWidth={1} />
                                <p className="text-sm font-bold text-slate-300 uppercase tracking-tighter">Waiting for Input</p>
                            </div>
                        )}
                    </div>
                </div>

                <button 
                    onClick={handleFitting}
                    disabled={isLoading || !humanFile || !garmentFile}
                    className="w-full py-5 bg-slate-900 text-white text-lg font-black rounded-2xl hover:bg-indigo-600 transition-all disabled:opacity-30 disabled:hover:bg-slate-900 shadow-xl shadow-slate-200 flex items-center justify-center gap-3"
                >
                    {isLoading ? (
                        <>
                            <RefreshCw size={20} className="animate-spin" />
                            MODIFY 피팅 분석 중...
                        </>
                    ) : (
                        <>
                            가상 피팅 시작하기
                            <CheckCircle size={20} />
                        </>
                    )}
                </button>

                <div className="my-24 border-t border-slate-100" />

                {/* [로직 유지] 피팅 히스토리 갤러리: 깔끔한 카드 스타일 */}
                <section className="mb-32">
                    <div className="flex items-end gap-3 mb-10">
                        <h2 className="text-3xl font-black text-slate-900">Fitting History</h2>
                        <span className="text-indigo-600 font-black mb-1">{history.length}</span>
                    </div>

                    {history.length === 0 ? (
                        <div className="text-center py-20 bg-slate-50 rounded-3xl text-slate-400 font-medium">
                            아직 피팅 기록이 없네요. 새로운 스타일을 시도해보세요!
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-6">
                            {history.map((item) => (
                                <div key={item.id} className="group relative bg-white border border-slate-100 rounded-3xl overflow-hidden hover:shadow-2xl transition-all">
                                    <div className="aspect-[3/4] bg-slate-50 overflow-hidden">
                                        <img src={item.result_image_url} alt="Result" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                                    </div>
                                    <div className="absolute inset-0 bg-slate-900/60 opacity-0 group-hover:opacity-100 transition-all flex flex-col items-center justify-center gap-3 backdrop-blur-[2px]">
                                        <button onClick={() => setSelectedImage(item.result_image_url)} className="bg-white text-slate-900 px-4 py-2 rounded-xl text-xs font-black hover:scale-105 transition-transform flex items-center gap-2">
                                            <Maximize2 size={14} /> 상세보기
                                        </button>
                                        
                                        {/* [수정] 장바구니 대신 삭제 버튼 배치 */}
                                        <button 
                                            onClick={() => handleDelete(item.id)} 
                                            className="bg-red-500 text-white px-4 py-2 rounded-xl text-xs font-black hover:bg-red-600 hover:scale-105 transition-all flex items-center gap-2"
                                        >
                                            <Trash2 size={14} /> 삭제하기
                                        </button>
                                    </div>
                                    <div className="p-4 flex items-center justify-between">
                                        <span className="text-[10px] font-black uppercase tracking-tighter text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">
                                            {item.category === 'upper_body' ? 'Top' : item.category === 'lower_body' ? 'Bottom' : 'Dress'}
                                        </span>
                                        <p className="text-[10px] text-slate-300 font-medium">
                                            {new Date(item.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </section>

                {/* [로직 유지] 이미지 확대 보기 모달 */}
                {selectedImage && (
                    <div 
                        className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/90 backdrop-blur-xl p-6 cursor-pointer"
                        onClick={() => setSelectedImage(null)}
                    >
                        <div className="relative max-w-2xl w-full flex justify-center animate-in zoom-in-95 duration-300">
                            <img src={selectedImage} alt="Enlarged" className="max-w-full max-h-[85vh] object-contain rounded-3xl shadow-2xl border border-white/10" onClick={(e) => e.stopPropagation()} />
                            <button onClick={() => setSelectedImage(null)} className="absolute -top-12 right-0 text-white/50 hover:text-white transition-colors">
                                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}