export default {
    props: { theme: { type: String, required: true } },
    emits: ['theme-changed'],
    data() { return { saving: false, error: '' } },
    methods: {
        async changeTheme(event) {
            const previousTheme = this.theme;
            const nextTheme = event.target.checked ? 'LIGHT' : 'DARK';
            this.error = '';
            this.$emit('theme-changed', nextTheme);
            this.saving = true;
            try {
                const response = await fetch('/api/v1/settings/theme', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ theme: nextTheme })
                });
                if (!response.ok) throw new Error();
            } catch (_) {
                this.$emit('theme-changed', previousTheme);
                this.error = 'Não foi possível salvar a preferência local.';
            } finally {
                this.saving = false;
            }
        }
    },
    template: `
        <section class="w-full">
            <div class="mb-8"><p class="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">Preferências locais</p><h1 class="mt-2 text-2xl font-bold text-slate-100">Configurações</h1><p class="mt-2 text-sm text-slate-400">Personalize esta cópia do Arkan.</p></div>
            <div class="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <div class="flex items-center justify-between gap-6">
                    <div><h2 class="font-semibold text-slate-100">Tema da interface</h2><p class="mt-1 text-sm text-slate-400">{{ theme === 'DARK' ? 'Escuro' : 'Claro' }}</p></div>
                    <label class="relative inline-flex cursor-pointer items-center" :class="{ 'opacity-60': saving }">
                        <input type="checkbox" class="peer sr-only" :checked="theme === 'LIGHT'" :disabled="saving" @change="changeTheme">
                        <span class="h-7 w-12 rounded-full bg-slate-700 transition peer-checked:bg-cyan-500"></span>
                        <span class="absolute left-1 h-5 w-5 rounded-full bg-white transition peer-checked:translate-x-5"></span>
                    </label>
                </div>
                <p v-if="error" class="mt-4 text-sm text-rose-400">{{ error }}</p>
            </div>
        </section>`
}
