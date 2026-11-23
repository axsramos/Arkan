// Componente orquestrador de autenticação local.
import UnlockNodeComponent from './UnlockNodeComponent.js';
import CreateNetworkComponent from './CreateNetworkComponent.js';

export default {
    name: 'AuthView',
    components: {
        CreateNetworkComponent,
        UnlockNodeComponent
    },
    emits: ['authenticated'],
    data() {
        return {
            isCheckingSetup: true,
            isNodeConfigured: false,
            isRecovering: false,
            setupError: ''
        }
    },
    async mounted() {
        await this.checkSetup();
    },
    methods: {
        async checkSetup() {
            this.isCheckingSetup = true;
            this.setupError = '';
        try {
            const response = await fetch('/api/v1/auth/check-setup');
            if (!response.ok) throw new Error('Resposta inválida do serviço local.');
            const data = await response.json();
            this.isNodeConfigured = data.is_configured;
        } catch (error) {
            this.setupError = 'Não foi possível verificar o estado do nó local. Confirme se o serviço Arkan está em execução.';
        } finally {
            this.isCheckingSetup = false;
        }
        },
        handleAuthenticated(payload) {
            this.$emit('authenticated', payload);
        }
    },
    template: `
        <div class="flex-1 flex flex-col w-full h-full">
            <div v-if="isCheckingSetup" class="flex-1 flex items-center justify-center p-4 text-sm text-slate-400">
                Verificando o nó local…
            </div>
            <div v-else-if="setupError" class="flex-1 flex items-center justify-center p-4">
                <div class="w-full max-w-md rounded-2xl border border-red-900/50 bg-slate-900/80 p-8 text-center space-y-4">
                    <p class="text-sm text-red-300">{{ setupError }}</p>
                    <button @click="checkSetup" class="rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700">Tentar novamente</button>
                </div>
            </div>
            <UnlockNodeComponent
                v-else-if="isNodeConfigured && !isRecovering"
                @node-unlocked="handleAuthenticated" @recover-access="isRecovering=true"
            />

            <!-- Caso contrário, exibe o fluxo de primeiro acesso -->
            <template v-else>
                <CreateNetworkComponent 
                    :initial-mode="isRecovering ? 'recover' : ''" @setup-completed="handleAuthenticated"
                />
            </template>
        </div>
    `
}
