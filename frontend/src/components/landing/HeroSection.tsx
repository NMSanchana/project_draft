import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { HeroData } from '@/types/landing/landing';
import { Container } from '@/components/ui/Container';
import { PlayCircle, Check, BarChart2, Database, MessageSquare, X, Play, Pause, Volume2, VolumeX, Maximize, Minimize, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface HeroSectionProps {
  data: HeroData;
  locale?: string;
}

export function HeroSection({ data, locale = 'en' }: HeroSectionProps) {
  const [isVideoOpen, setIsVideoOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);

  const videoRef = useRef<HTMLVideoElement>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);
  const hideControlsTimeout = useRef<NodeJS.Timeout | null>(null);

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const current = videoRef.current.currentTime;
      const dur = videoRef.current.duration || 0;
      setCurrentTime(current);
      setDuration(dur);
      setProgress(dur > 0 ? (current / dur) * 100 : 0);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekPercent = parseFloat(e.target.value);
    if (videoRef.current && duration > 0) {
      const newTime = (seekPercent / 100) * duration;
      videoRef.current.currentTime = newTime;
      setProgress(seekPercent);
    }
  };

  const toggleFullscreen = () => {
    if (!playerContainerRef.current) return;
    if (!document.fullscreenElement) {
      playerContainerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  const formatTime = (timeInSeconds: number) => {
    const mins = Math.floor(timeInSeconds / 60);
    const secs = Math.floor(timeInSeconds % 60);
    return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const handleMouseMove = () => {
    setControlsVisible(true);
    if (hideControlsTimeout.current) clearTimeout(hideControlsTimeout.current);
    hideControlsTimeout.current = setTimeout(() => {
      if (isPlaying) setControlsVisible(false);
    }, 3000);
  };

  useEffect(() => {
    if (isVideoOpen && videoRef.current) {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  }, [isVideoOpen]);

  return (
    <div className="relative pt-32 pb-20 overflow-hidden bg-gradient-to-br from-[var(--bg-gradient-start)] to-[var(--bg-gradient-end)] min-h-[90vh] flex items-center">
      <Container className="grid lg:grid-cols-2 gap-12 items-center">
        {/* Left Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-2xl"
        >
          <h1 className="text-5xl lg:text-7xl font-bold text-[var(--ink)] leading-[1.1] mb-6">
            {data.titleLine1} <br />
            {data.titleLine2} <br />
            <span className="relative inline-block">
              {data.titleLine3}
              <svg className="absolute -bottom-3 left-0 w-full" viewBox="0 0 300 15" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2 13C60.5 4 150 -2 298 7" stroke="var(--brand)" strokeWidth="4" strokeLinecap="round" />
              </svg>
            </span>
          </h1>
          <p className="text-[var(--ink-light)] text-lg mb-10 max-w-lg leading-relaxed">
            {data.description}
          </p>
          <div className="flex flex-wrap items-center gap-6">
            <Link
              href={
                data.primaryButtonHref
                  ? data.primaryButtonHref === '/login'
                    ? `/${locale}/login`
                    : data.primaryButtonHref
                  : `/${locale}/login`
              }
              className="bg-[var(--brand)] text-white px-8 py-4 rounded-full font-semibold hover:bg-[var(--brand-hover)] transition-all duration-300 transform hover:-translate-y-1 shadow-lg shadow-[var(--brand)]/30 animate-pulse-glow inline-flex items-center justify-center cursor-pointer"
            >
              {data.primaryButtonText}
            </Link>
            <button 
              onClick={() => setIsVideoOpen(true)}
              className="flex items-center gap-3 text-[var(--ink)] font-semibold hover:text-[var(--brand)] transition-all duration-300 transform hover:scale-105 group cursor-pointer"
            >
              <PlayCircle size={28} className="text-[var(--ink-light)] group-hover:text-[var(--brand)] transition-colors" />
              {data.secondaryButtonText}
            </button>
          </div>
        </motion.div>

        {/* Right Graphics */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative h-[600px] w-full"
        >
          <div className="absolute inset-0 right-0 left-auto w-[85%] h-full bg-[var(--brand)] rounded-3xl overflow-hidden shadow-2xl">
            <svg className="absolute inset-0 w-full h-full text-white/10" viewBox="0 0 400 400" preserveAspectRatio="none">
              <path d="M0,200 L50,150 L100,250 L150,100 L200,300 L250,50 L300,350 L350,150 L400,200" stroke="currentColor" strokeWidth="8" fill="none" strokeLinejoin="round" />
            </svg>
            <img src={data.heroImage} alt={data.heroImageAlt} className="absolute bottom-0 left-1/2 -translate-x-1/2 h-[90%] object-cover object-top mask-image-bottom" />
          </div>

          {/* Floating Cards */}
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
            className="absolute top-10 -left-6 bg-white p-4 rounded-xl shadow-[var(--shadow-lg)] flex items-center justify-between w-64 z-10"
          >
            <div>
              <p className="text-xs text-gray-400 font-medium mb-1">Enter amount</p>
              <p className="text-lg font-bold">$450..00</p>
            </div>
            <button className="bg-[var(--brand)] text-white text-xs font-semibold px-4 py-2 rounded-full">Send</button>
          </motion.div>

          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
            className="absolute top-1/2 left-0 bg-[var(--brand-dark)] text-white w-8 h-8 rounded-lg flex items-center justify-center shadow-lg z-10"
          >
            <Check size={16} />
          </motion.div>

          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 3.5, ease: "easeInOut" }}
            className="absolute bottom-1/4 -left-4 bg-white p-4 rounded-xl shadow-[var(--shadow-lg)] flex items-center justify-between gap-4 w-48 z-10"
          >
            <div>
              <p className="text-xs text-gray-400 font-medium mb-1">Total Income</p>
              <p className="text-lg font-bold">$245.00</p>
            </div>
            <div className="text-[var(--brand)]"><BarChart2 size={24} /></div>
          </motion.div>

          <motion.div
            animate={{ y: [0, -12, 0], rotate: [0, -2, 0] }}
            transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
            className="absolute right-0 bottom-1/4 translate-x-1/4 bg-[#1a1c29] text-white p-5 rounded-2xl shadow-[var(--shadow-lg)] w-60 z-10"
          >
            <div className="flex justify-between items-start mb-6">
              <div className="flex gap-1">
                <div className="w-6 h-6 rounded-full bg-white/20"></div>
                <div className="w-6 h-6 rounded-full bg-white/20 -ml-3"></div>
              </div>
            </div>
            <p className="text-sm font-medium mb-1">Credit Crad</p>
            <p className="text-lg tracking-widest mb-4">**** 1234</p>
            <div className="flex justify-between items-end">
              <div className="w-8 h-6 bg-white/20 rounded"></div>
              {/* <p className="text-xs">09/25</p> */}
            </div>
          </motion.div>

          {/* Decorative small icons */}
          <div className="absolute top-8 right-8 bg-yellow-400 p-2 rounded-lg rotate-12 shadow-md z-10 text-white">
            <Database size={20} />
          </div>
          <div className="absolute bottom-8 right-16 bg-orange-400 p-2 rounded-lg -rotate-12 shadow-md z-10 text-white">
            <MessageSquare size={20} />
          </div>

        </motion.div>
      </Container>

      {/* Transparent Glassmorphism Video Modal Player */}
      <AnimatePresence>
        {isVideoOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsVideoOpen(false)}
            className="fixed inset-0 bg-black/50 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-6 md:p-10 overflow-y-auto"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 20 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-5xl bg-[#161c28]/85 backdrop-blur-lg rounded-2xl overflow-hidden shadow-2xl border border-white/10 flex flex-col my-auto"
            >
              {/* Modal Header Bar */}
              <div className="flex justify-between items-center px-6 py-4 border-b border-white/10 bg-white/5">
                <h3 className="text-white font-bold text-lg md:text-xl tracking-wide">
                  Platform Interactive Demo
                </h3>
                <button
                  onClick={() => setIsVideoOpen(false)}
                  className="w-9 h-9 rounded-full bg-white/10 hover:bg-[#54bd95] text-white flex items-center justify-center transition-colors duration-200 cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Custom Video Player Container */}
              <div 
                ref={playerContainerRef}
                onMouseMove={handleMouseMove}
                className="relative aspect-video w-full bg-black/40 backdrop-blur-md flex items-center justify-center group overflow-hidden"
              >
                {data.demoVideoUrl ? (
                  <>
                    <video
                      ref={videoRef}
                      src={data.demoVideoUrl}
                      onTimeUpdate={handleTimeUpdate}
                      onClick={togglePlay}
                      playsInline
                      className="w-full h-full object-contain cursor-pointer"
                    />

                    {/* Central Play/Pause Flash Overlay */}
                    <button
                      onClick={togglePlay}
                      className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 cursor-pointer"
                    >
                      <motion.div 
                        whileHover={{ scale: 1.15 }}
                        whileTap={{ scale: 0.9 }}
                        className="w-20 h-20 rounded-full bg-[#54bd95]/90 text-white flex items-center justify-center shadow-[0_0_30px_#54bd95] backdrop-blur-sm border border-white/20"
                      >
                        {isPlaying ? <Pause size={36} /> : <Play size={36} className="ml-1.5" />}
                      </motion.div>
                    </button>

                    {/* Customized Control Bar */}
                    <motion.div
                      animate={{ opacity: controlsVisible ? 1 : 0, y: controlsVisible ? 0 : 20 }}
                      transition={{ duration: 0.3 }}
                      className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-[#161c28] via-[#161c28]/80 to-transparent p-4 sm:p-6 flex flex-col gap-3 pointer-events-auto"
                    >
                      {/* Theme-styled Scrubber Bar */}
                      <div className="relative w-full flex items-center group/slider cursor-pointer">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={progress}
                          onChange={handleSeek}
                          className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer accent-[#54bd95] focus:outline-none"
                          style={{
                            background: `linear-gradient(to right, #54bd95 ${progress}%, rgba(255, 255, 255, 0.2) ${progress}%)`
                          }}
                        />
                      </div>

                      {/* Controls Row */}
                      <div className="flex items-center justify-between gap-4 text-white text-sm">
                        <div className="flex items-center gap-4">
                          {/* Play / Pause Toggle */}
                          <button
                            onClick={togglePlay}
                            className="p-2 rounded-lg bg-white/10 hover:bg-[#54bd95] text-white transition-all duration-200 cursor-pointer shadow-md"
                          >
                            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
                          </button>

                          {/* Volume Toggle */}
                          <button
                            onClick={toggleMute}
                            className="p-2 rounded-lg bg-white/10 hover:bg-[#54bd95] text-white transition-all duration-200 cursor-pointer shadow-md"
                          >
                            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
                          </button>

                          {/* Time Counter */}
                          <span className="font-mono text-xs sm:text-sm text-gray-300 font-semibold tracking-wider">
                            {formatTime(currentTime)} / {formatTime(duration)}
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          {/* Fullscreen Toggle */}
                          <button
                            onClick={toggleFullscreen}
                            className="p-2 rounded-lg bg-white/10 hover:bg-[#54bd95] text-white transition-all duration-200 cursor-pointer shadow-md"
                          >
                            {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  </>
                ) : (
                  <div className="text-gray-400 text-center p-8">
                    <p className="text-xl font-bold mb-2">No Video Specified</p>
                    <p className="text-sm">Please set demoVideoUrl in src/data/landing/en.ts</p>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
