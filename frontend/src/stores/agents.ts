/** Agents store: list + current agent + sources for the detail page. */
import { ref } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api/client'
import type { Agent, Source } from '@/api/types'
import { useAuthStore } from './auth'

export const useAgentsStore = defineStore('agents', () => {
  const auth = useAuthStore()
  const agents = ref<Agent[]>([])
  const current = ref<Agent | null>(null)
  const sources = ref<Source[]>([])

  async function fetchAgents() {
    agents.value = await api.listAgents(auth.token)
  }

  async function fetchAgent(id: number) {
    current.value = await api.getAgent(auth.token, id)
  }

  async function create(data: Partial<Agent>) {
    const agent = await api.createAgent(auth.token, data)
    agents.value.unshift(agent)
    return agent
  }

  async function update(data: Partial<Agent>) {
    if (!current.value) return
    current.value = await api.updateAgent(auth.token, current.value.id, data)
  }

  async function remove(id: number) {
    await api.deleteAgent(auth.token, id)
    agents.value = agents.value.filter((a) => a.id !== id)
    if (current.value?.id === id) current.value = null
  }

  async function regenerateToken() {
    if (!current.value) return
    current.value = await api.regenerateToken(auth.token, current.value.id)
  }

  async function uploadAvatar(file: File, kind: 'photo' | 'template' = 'photo') {
    if (!current.value) return
    current.value = await api.uploadAgentAvatar(auth.token, current.value.id, file, kind)
  }

  async function removeAvatar() {
    if (!current.value) return
    current.value = await api.deleteAgentAvatar(auth.token, current.value.id)
  }

  async function fetchSources(agentId: number) {
    sources.value = await api.listSources(auth.token, agentId)
  }

  async function addSources(agentId: number, urls: string[]) {
    const created = await api.addSources(auth.token, agentId, urls)
    sources.value = [...created, ...sources.value]
    return created
  }

  async function deleteSource(agentId: number, sourceId: number) {
    await api.deleteSource(auth.token, agentId, sourceId)
    sources.value = sources.value.filter((s) => s.id !== sourceId)
  }

  async function reindex(agentId: number, onlyFailed = false) {
    await api.reindexSources(auth.token, agentId, onlyFailed)
  }

  return {
    agents,
    current,
    sources,
    fetchAgents,
    fetchAgent,
    create,
    update,
    remove,
    regenerateToken,
    uploadAvatar,
    removeAvatar,
    fetchSources,
    addSources,
    deleteSource,
    reindex,
  }
})
