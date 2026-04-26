import { defineStore } from 'pinia'
import { ref } from 'vue'
import { portfolioApi } from '@/api/portfolio'
import { profileApi } from '@/api/profile'
import type { Position, PortfolioSummary, AnalysisReport, CreatePositionRequest, Transaction, CreateTransactionRequest } from '@/types/portfolio'
import type { BrokerProfile } from '@/api/profile'

export const usePortfolioStore = defineStore('portfolio', () => {
  const positions = ref<Position[]>([])
  const summary = ref<PortfolioSummary | null>(null)
  const analysis = ref<AnalysisReport | null>(null)
  const transactions = ref<Transaction[]>([])
  const loading = ref(false)

  // Profile state
  const profiles = ref<BrokerProfile[]>([])
  const activeProfileId = ref<string>('')

  const fetchPositions = async () => {
    loading.value = true
    try {
      const params: { include_inactive?: boolean; profile_id?: string } = {}
      if (activeProfileId.value) {
        params.profile_id = activeProfileId.value
      }
      const response = await portfolioApi.getPositions(params)
      positions.value = Array.isArray(response) ? response : []
    } catch (e) {
      positions.value = []
    } finally {
      loading.value = false
    }
  }

  const addPosition = async (data: CreatePositionRequest) => {
    loading.value = true
    try {
      const payload = { ...data }
      if (activeProfileId.value && !payload.profile_id) {
        payload.profile_id = activeProfileId.value
      }
      await portfolioApi.createPosition(payload)
      await fetchPositions()
      await fetchSummary()
    } finally {
      loading.value = false
    }
  }

  const deletePosition = async (id: string) => {
    try {
      await portfolioApi.deletePosition(id)
      positions.value = positions.value.filter(p => p.id !== id)
      await fetchSummary()
    } catch (e) {
      // Error handled by interceptor
    }
  }

  const fetchSummary = async () => {
    try {
      const params: Record<string, string> = {}
      if (activeProfileId.value) {
        params.profile_id = activeProfileId.value
      }
      const response = await portfolioApi.getSummary(params)
      summary.value = response || null
    } catch (e) {
      // Error handled by interceptor
    }
  }

  const fetchAnalysis = async (date?: string) => {
    try {
      const today = date || new Date().toISOString().split('T')[0]
      const response = await portfolioApi.getAnalysisReport(today)
      analysis.value = response || null
    } catch (e) {
      // Error handled by interceptor
    }
  }

  const triggerDailyAnalysis = async () => {
    loading.value = true
    try {
      await portfolioApi.triggerDailyAnalysis()
      await fetchAnalysis()
    } catch (e) {
      // Error handled by interceptor
    } finally {
      loading.value = false
    }
  }

  // ---- Profile actions ----
  const fetchProfiles = async () => {
    try {
      const response = await profileApi.list()
      profiles.value = Array.isArray(response) ? response : []
      // If no active profile, select the default one
      if (!activeProfileId.value && profiles.value.length) {
        const defaultProfile = profiles.value.find(p => p.is_default)
        activeProfileId.value = defaultProfile?.id || profiles.value[0].id
      }
    } catch (e) {
      profiles.value = []
    }
  }

  const setActiveProfile = async (profileId: string) => {
    activeProfileId.value = profileId
    await Promise.all([fetchPositions(), fetchSummary()])
  }

  const createProfile = async (data: { name: string; broker?: string; is_default?: boolean }) => {
    const newProfile = await profileApi.create(data)
    await fetchProfiles()
    if (data.is_default || profiles.value.length === 1) {
      activeProfileId.value = newProfile.id
    }
    return newProfile
  }

  const updateProfile = async (profileId: string, data: { name?: string; broker?: string }) => {
    const updated = await profileApi.update(profileId, data)
    await fetchProfiles()
    return updated
  }

  const deleteProfile = async (profileId: string) => {
    await profileApi.delete(profileId)
    if (activeProfileId.value === profileId) {
      activeProfileId.value = ''
    }
    await fetchProfiles()
  }

  // ---- Transaction actions ----
  const buyTransaction = async (data: CreateTransactionRequest) => {
    loading.value = true
    try {
      const payload = { ...data }
      if (activeProfileId.value && !payload.profile_id) {
        payload.profile_id = activeProfileId.value
      }
      await portfolioApi.buyTransaction(payload)
      await Promise.all([fetchPositions(), fetchSummary(), fetchTransactions()])
    } finally {
      loading.value = false
    }
  }

  const sellTransaction = async (data: CreateTransactionRequest) => {
    loading.value = true
    try {
      const payload = { ...data }
      if (activeProfileId.value && !payload.profile_id) {
        payload.profile_id = activeProfileId.value
      }
      await portfolioApi.sellTransaction(payload)
      await Promise.all([fetchPositions(), fetchSummary(), fetchTransactions()])
    } finally {
      loading.value = false
    }
  }

  const fetchTransactions = async (params?: { ts_code?: string; start_date?: string; end_date?: string; profile_id?: string }) => {
    try {
      const queryParams: Record<string, string> = { ...params } as Record<string, string>
      if (activeProfileId.value) {
        queryParams.profile_id = activeProfileId.value
      }
      const response = await portfolioApi.getTransactions(queryParams)
      transactions.value = Array.isArray(response) ? response : []
    } catch (e) {
      transactions.value = []
    }
  }

  return {
    positions,
    summary,
    analysis,
    transactions,
    loading,
    profiles,
    activeProfileId,
    fetchPositions,
    addPosition,
    deletePosition,
    fetchSummary,
    fetchAnalysis,
    triggerDailyAnalysis,
    fetchProfiles,
    setActiveProfile,
    createProfile,
    updateProfile,
    deleteProfile,
    buyTransaction,
    sellTransaction,
    fetchTransactions
  }
})
