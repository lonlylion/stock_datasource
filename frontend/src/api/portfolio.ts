import request from '@/utils/request'
import type {
  Position,
  PortfolioSummary,
  CreatePositionRequest,
  UpdatePositionRequest,
  AnalysisReport,
  AlertCreateRequest,
  Transaction,
  CreateTransactionRequest,
  TransactionSignal,
  KlinePattern
} from '@/types/portfolio'

export const portfolioApi = {
  // Position management
  getPositions(params?: { include_inactive?: boolean; profile_id?: string }) {
    return request.get<Position[]>('/api/portfolio/positions', { params })
  },

  createPosition(data: CreatePositionRequest) {
    return request.post<Position>('/api/portfolio/positions', data)
  },

  updatePosition(id: string, data: UpdatePositionRequest) {
    return request.put<Position>(`/api/portfolio/positions/${id}`, data)
  },

  deletePosition(id: string) {
    return request.delete(`/api/portfolio/positions/${id}`)
  },

  // Portfolio summary
  getSummary(params?: { profile_id?: string }) {
    return request.get<PortfolioSummary>('/api/portfolio/summary', { params })
  },

  getProfitHistory(days: number = 30) {
    return request.get('/api/portfolio/profit-history', { 
      params: { days } 
    })
  },

  // Analysis
  triggerDailyAnalysis(analysisDate?: string) {
    return request.post('/api/portfolio/daily-analysis', {
      analysis_date: analysisDate
    })
  },

  getAnalysisReport(reportDate?: string) {
    return request.get<AnalysisReport>('/api/portfolio/analysis', {
      params: reportDate ? { date: reportDate } : {}
    })
  },

  getAnalysisHistory(days: number = 30) {
    return request.get<AnalysisReport[]>('/api/portfolio/analysis', {
      params: { days }
    })
  },

  // Alerts
  createAlert(data: AlertCreateRequest) {
    return request.post('/api/portfolio/alerts', data)
  },

  checkAlerts() {
    return request.get('/api/portfolio/alerts/check')
  },

  // Batch operations
  batchUpdatePrices() {
    return request.post('/api/portfolio/batch/update-prices')
  },

  // Transactions
  buyTransaction(data: CreateTransactionRequest) {
    return request.post<Transaction>('/api/portfolio/transactions/buy', data)
  },

  sellTransaction(data: CreateTransactionRequest) {
    return request.post<Transaction>('/api/portfolio/transactions/sell', data)
  },

  getTransactions(params?: { ts_code?: string; start_date?: string; end_date?: string; profile_id?: string }) {
    return request.get<Transaction[]>('/api/portfolio/transactions', { params })
  },

  // Transaction signals for K-line markers
  getTransactionSignals(params: { ts_code: string; start_date?: string; end_date?: string }) {
    return request.get<TransactionSignal[]>('/api/portfolio/transactions/signals', { params })
  },

  // K-line candlestick patterns
  getKlinePatterns(tsCode: string, days: number = 60) {
    return request.get<KlinePattern[]>(`/api/portfolio/kline-patterns/${tsCode}`, { params: { days } })
  }
}