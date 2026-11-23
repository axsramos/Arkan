export default {
    name: 'UnlockNodeComponent',
    emits: ['node-unlocked', 'recover-access'],
    data() { return { errorMessage: '', isLoading: false } },
    template: `
        <div class="flex-1 flex items-center justify-center p-4 bg-slate-950">
            <div class="w-full max-w-md space-y-5 rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-center shadow-2xl">
                <span class="text-xs px-2.5 py-1 bg-cyan-950 text-cyan-400 border border-cyan-800/50 rounded-md font-medium">Nó protegido</span>
                <div><h1 class="text-3xl font-black text-slate-100">Desbloquear cofre</h1><p class="mt-2 text-xs text-slate-400">O PIN será solicitado somente no diálogo local do aplicativo.</p></div>
                <button @click="request('/api/v1/auth/unlock')" :disabled="isLoading" class="w-full rounded-xl bg-cyan-600 py-3.5 font-medium text-white">{{ isLoading ? 'Aguardando diálogo local…' : 'Desbloquear nó' }}</button>
                <button @click="$emit('recover-access')" :disabled="isLoading" class="w-full text-xs text-cyan-400 underline">Esqueci o PIN: recuperar com credencial</button>
                <p v-if="errorMessage" class="rounded-lg border border-red-900/50 bg-red-950/30 py-2 text-xs text-red-400">{{ errorMessage }}</p>
            </div>
        </div>`,
    methods: {
        async request(path) {
            this.errorMessage = ''; this.isLoading = true;
            try {
                const response = await fetch(path, { method: 'POST', credentials: 'same-origin' });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) { this.errorMessage = data.detail || 'Não foi possível concluir a operação local.'; return; }
                this.$emit('node-unlocked', { pseudonym: data.pseudonym, role: data.role });
            } catch (_) { this.errorMessage = 'Erro de conexão com o backend local.'; }
            finally { this.isLoading = false; }
        }
    }
}
