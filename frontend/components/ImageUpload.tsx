/**
 * Image Upload Component with OCR
 */
"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface ImageUploadProps {
  onAnalysisComplete: (results: any) => void;
  onError: (error: string) => void;
  cardLayout?: boolean;
}

export default function ImageUpload({
  onAnalysisComplete,
  onError,
  cardLayout = false,
}: ImageUploadProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleImageSelect = (file: File) => {
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);
    setSelectedFile(file);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    try {
      const results = await api.analyzeImage(selectedFile);
      onAnalysisComplete(results);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      console.error("Analysis error details:", errorMessage);
      onError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      handleImageSelect(file);
    }
  };

  if (cardLayout) {
    return (
      <div className="w-full space-y-4">
        <div
          onDragOver={() => setIsDragging(true)}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-all duration-300 ${
            isDragging
              ? "border-forest-700 bg-sage-100 scale-105"
              : "border-sage-300 hover:border-sage-400 hover:bg-sage-50"
          }`}
        >
          <input
            type="file"
            accept="image/*"
            onChange={(e) =>
              e.target.files?.[0] && handleImageSelect(e.target.files[0])
            }
            className="hidden"
            id="image-input"
          />
          <label htmlFor="image-input" className="cursor-pointer block">
            <div className="text-3xl mb-2">📷</div>
            <p className="text-sage-700 font-semibold text-sm mb-1">
              Click or drag to upload
            </p>
            <p className="text-sage-600 text-xs">JPG, PNG • Max 5MB</p>
          </label>
        </div>

        {preview && (
          <div className="space-y-3 animate-in fade-in">
            <div className="rounded-lg overflow-hidden border border-sage-200 bg-white p-2 max-h-40">
              <img
                src={preview}
                alt="Preview"
                className="max-w-full h-auto rounded max-h-36 mx-auto"
              />
            </div>
            <div className="flex gap-2 flex-col">
              <button
                onClick={handleAnalyze}
                disabled={isLoading}
                className="btn-primary"
              >
                {isLoading ? "🔄 Analyzing..." : "✓ Analyze"}
              </button>
              <button
                onClick={() => {
                  setPreview(null);
                  setSelectedFile(null);
                }}
                disabled={isLoading}
                className="btn-secondary"
              >
                ✕ Clear
              </button>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-6 animate-in fade-in">
            <div className="inline-block mb-3">
              <div className="animate-spin rounded-full h-10 w-10 border-4 border-sage-300 border-t-forest-700"></div>
            </div>
            <p className="text-sage-700 font-semibold text-sm">
              Extracting ingredients...
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      <div
        onDragOver={() => setIsDragging(true)}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 ${
          isDragging
            ? "border-forest-700 bg-sage-100 scale-105"
            : "border-sage-400 hover:border-forest-700 hover:bg-sage-50"
        }`}
      >
        <input
          type="file"
          accept="image/*"
          onChange={(e) =>
            e.target.files?.[0] && handleImageSelect(e.target.files[0])
          }
          className="hidden"
          id="image-input"
        />
        <label htmlFor="image-input" className="cursor-pointer">
          <div className="mb-4">
            <div className="inline-block text-5xl mb-3">📷</div>
          </div>
          <p className="text-forest-800 font-bold text-lg mb-2">
            Upload Product Label Image
          </p>
          <p className="text-sage-700 text-sm mb-3">
            Drag and drop or click to select
          </p>
          <p className="text-sage-600 text-xs">JPG, PNG, GIF • Max 5MB</p>
        </label>
      </div>

      {preview && (
        <div className="space-y-4 animate-in fade-in">
          <div className="rounded-xl overflow-hidden border border-sage-200 shadow-lg bg-white p-2">
            <img
              src={preview}
              alt="Preview"
              className="max-w-full h-auto rounded-lg max-h-80 mx-auto"
            />
          </div>
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleAnalyze}
              disabled={isLoading}
              className="px-8 py-3 bg-gradient-to-r from-forest-700 to-forest-600 text-white rounded-lg hover:shadow-lg disabled:bg-sage-300 disabled:cursor-not-allowed font-bold transition-all active:scale-95 text-sm"
            >
              {isLoading ? "🔄 Analyzing..." : "✓ Analyze Image"}
            </button>
            <button
              onClick={() => {
                setPreview(null);
                setSelectedFile(null);
              }}
              disabled={isLoading}
              className="px-8 py-3 bg-sage-200 text-forest-700 rounded-lg hover:bg-sage-300 disabled:cursor-not-allowed font-bold transition-all text-sm"
            >
              ✕ Clear
            </button>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="text-center py-12 animate-in fade-in">
          <div className="inline-block mb-4">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-sage-300 border-t-forest-700"></div>
          </div>
          <p className="text-sage-700 font-medium">
            Analyzing image and extracting ingredients...
          </p>
          <p className="text-sage-600 text-sm mt-1">
            This may take a few seconds
          </p>
        </div>
      )}
    </div>
  );
}
