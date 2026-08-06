<script setup lang="ts">
import { ref } from 'vue'

const file = ref<File | null>(null)
const dragging = ref(false)
const loading = ref(false)
const result = ref<{ text: string; model: string; input_tokens: number; output_tokens: number } | null>(null)
const error = ref('')

function onDrop(e: DragEvent) {
  dragging.value = false
  const dropped = e.dataTransfer?.files[0]
  if (dropped && dropped.type === 'application/pdf') {
    file.value = dropped
    error.value = ''
  } else {
    error.value = 'Please drop a PDF file.'
  }
}

function onFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    file.value = target.files[0]
    error.value = ''
  }
}

async function analyze() {
  if (!file.value) return
  loading.value = true
  result.value = null
  error.value = ''

  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const res = await fetch('http://localhost:8000/api/analyze', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => null)
      throw new Error(detail?.detail || `Server error: ${res.status}`)
    }
    result.value = await res.json()
  } catch (e: any) {
    error.value = e.message || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

function reset() {
  file.value = null
  result.value = null
  error.value = ''
}
</script>

<template>
  <div class="app">
    <header>
      <h1>AFP Compliance Analyzer</h1>
      <p class="subtitle">Drop a movie script PDF and get an AFP legislation compliance analysis</p>
    </header>

    <main>
      <!-- Drop zone -->
      <div
        v-if="!result && !loading"
        class="dropzone"
        :class="{ active: dragging }"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="onDrop"
      >
        <div class="dropzone-content">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <polyline points="9 15 12 12 15 15"/>
          </svg>
          <p>Drag & drop a movie script PDF here</p>
          <span>or</span>
          <label class="file-btn">
            Browse files
            <input type="file" accept=".pdf" @change="onFileSelect" hidden />
          </label>
        </div>
      </div>

      <!-- File selected -->
      <div v-if="file && !result && !loading" class="file-info">
        <p><strong>Selected:</strong> {{ file.name }}</p>
        <button class="btn primary" @click="analyze">Analyze Compliance</button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>Analyzing script against AFP legislation...</p>
        <p class="hint">This may take a minute for long scripts.</p>
      </div>

      <!-- Result -->
      <div v-if="result" class="result">
        <div class="result-header">
          <h2>Analysis Result</h2>
          <button class="btn secondary" @click="reset">Analyze Another</button>
        </div>
        <div class="result-body" v-html="formatText(result.text)"></div>
        <div class="meta">
          Model: {{ result.model }} |
          Input tokens: {{ result.input_tokens }} |
          Output tokens: {{ result.output_tokens }}
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="error">{{ error }}</div>
    </main>
  </div>
</template>

<script lang="ts">
function formatText(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
export default { methods: { formatText } }
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
  color: #1a1a2e;
  min-height: 100vh;
}
.app {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1rem;
}
header {
  text-align: center;
  margin-bottom: 2rem;
}
header h1 {
  font-size: 1.8rem;
  color: #1a1a2e;
}
.subtitle {
  color: #666;
  margin-top: 0.5rem;
}
.dropzone {
  border: 2px dashed #ccc;
  border-radius: 12px;
  padding: 3rem 2rem;
  text-align: center;
  transition: all 0.2s;
  background: white;
  cursor: pointer;
}
.dropzone.active {
  border-color: #3b82f6;
  background: #eff6ff;
}
.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: #666;
}
.dropzone-content svg {
  color: #9ca3af;
}
.file-btn {
  background: #3b82f6;
  color: white;
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.file-btn:hover {
  background: #2563eb;
}
.file-info {
  text-align: center;
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.btn {
  padding: 0.6rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  font-weight: 500;
}
.btn.primary {
  background: #3b82f6;
  color: white;
}
.btn.primary:hover {
  background: #2563eb;
}
.btn.secondary {
  background: #e5e7eb;
  color: #374151;
}
.btn.secondary:hover {
  background: #d1d5db;
}
.loading {
  text-align: center;
  padding: 3rem;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.hint {
  color: #9ca3af;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}
.result {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.result-body {
  line-height: 1.7;
  font-size: 0.95rem;
  white-space: pre-wrap;
}
.meta {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
  font-size: 0.8rem;
  color: #9ca3af;
}
.error {
  background: #fef2f2;
  color: #dc2626;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  text-align: center;
}
</style>
