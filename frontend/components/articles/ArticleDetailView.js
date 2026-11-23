export default {
    name: 'ArticleDetailView',
    props: { itemHash: { type: String, required: true } },
    emits: ['back', 'compose-comment', 'compose-version', 'open-item'],
    data() { return { item: null, comments: [], classification: null, editingClassification: false, categoryInput: '', badgesInput: '', error: '', message: '', isLoading: false }; },
    mounted() { this.load(); },
    watch: {
        itemHash() { this.load(); },
        item(value) { if (value) value.autor_id = value.autor_pseudonimo || value.autor_id; },
        comments(value) { value.forEach((comment) => { comment.autor_id = comment.autor_pseudonimo || comment.autor_id; }); },
    },
    template: `<section class="mx-auto max-w-4xl space-y-5">
      <button @click="$emit('back')" class="text-sm text-cyan-400 hover:text-cyan-300">← Voltar ao acervo</button>
      <div v-if="error" class="rounded-xl border border-red-900/60 bg-red-950/30 p-4 text-sm text-red-300">{{ error }}</div>
      <div v-else-if="!item" class="text-sm text-slate-400">Abrindo publicação…</div>
      <template v-else>
        <article class="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8">
          <div class="mb-5 flex flex-wrap items-center gap-2 text-xs"><span class="rounded-full border border-cyan-800/60 bg-cyan-950/50 px-2.5 py-1 text-cyan-300">{{ item.tipo === 'COMENTARIO' ? 'Comentário' : 'Artigo' }}</span><span v-if="item.anterior_hash" class="rounded-full border border-slate-700 px-2.5 py-1 text-slate-400">Nova versão</span><span class="text-slate-500">{{ formatDate(item.criado_em) }}</span></div>
          <h1 class="text-2xl font-bold tracking-tight text-slate-100">{{ item.titulo || 'Sem título' }}</h1><p class="mt-2 text-xs text-slate-500">Autoria: {{ item.autor_id }}</p>
          <button v-if="item.anterior_hash" @click="$emit('open-item', item.anterior_hash)" class="mt-3 text-xs text-cyan-400 hover:text-cyan-300">← Ver versão anterior</button>
          <div v-if="item.tem_corpo && !item.removido_localmente" class="mt-8 whitespace-pre-wrap break-words text-[15px] leading-7 text-slate-200">{{ item.corpo }}</div>
          <div v-else class="mt-8 rounded-xl border border-amber-900/60 bg-amber-950/30 p-4 text-sm text-amber-200">Esta cópia possui somente o resumo ou removeu o conteúdo local. Importe uma exportação completa para ler o corpo.</div>
          <div v-if="item.tipo === 'ARTIGO' && item.tem_corpo" class="mt-8 flex flex-wrap gap-2 border-t border-slate-800 pt-5"><button @click="$emit('compose-comment', item.hash)" class="rounded-xl bg-cyan-700 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-600">Comentar</button><button v-if="item.proprio" @click="$emit('compose-version', item)" class="rounded-xl bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700">Criar nova versão</button></div>
          <div v-if="!item.proprio" class="mt-8 border-t border-slate-800 pt-5"><button v-if="!item.removido_localmente && item.tem_corpo" @click="changeLocalAvailability('/api/v1/content/remove-local', 'Remover o conteúdo local deste artigo? O cabeçalho será preservado.')" :disabled="isLoading" class="rounded-xl px-4 py-2 text-sm text-amber-300 hover:bg-amber-950/40 disabled:opacity-50">Remover conteúdo local</button><button v-else-if="item.removido_localmente" @click="changeLocalAvailability('/api/v1/content/reimport')" :disabled="isLoading" class="rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700 disabled:opacity-50">Permitir nova importação</button></div>
          <p v-if="message" class="mt-4 text-sm text-emerald-400">{{ message }}</p>
        </article>
        <section v-if="item.tipo === 'ARTIGO' && classification" class="rounded-2xl border border-slate-800 bg-slate-900/60 p-5"><div class="flex items-center justify-between gap-3"><h2 class="text-sm font-semibold text-slate-200">Classificação local</h2><button @click="startClassification" class="text-xs text-cyan-400 hover:text-cyan-300">{{ editingClassification ? 'Cancelar' : 'Editar' }}</button></div><div v-if="!editingClassification" class="mt-3 flex flex-wrap gap-2"><span v-if="classification.categoria" class="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-200">{{ classification.categoria }}</span><span v-for="badge in classification.badges" :key="badge" class="rounded-full border border-cyan-900/70 px-2.5 py-1 text-xs text-cyan-300">{{ badge }}</span><span v-if="!classification.categoria && !classification.badges.length" class="text-sm text-slate-500">Sem categoria ou badges nesta cópia.</span></div><div v-else class="mt-4 space-y-3"><input v-model="categoryInput" list="categorias-locais" maxlength="80" placeholder="Categoria local" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"><datalist id="categorias-locais"><option v-for="category in classification.categorias_disponiveis" :key="category" :value="category"></option></datalist><input v-model="badgesInput" maxlength="819" placeholder="Badges separados por vírgula" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"><button @click="saveClassification" :disabled="isLoading" class="rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700">Salvar classificação</button></div></section>
        <section v-if="item.tipo === 'ARTIGO'" class="rounded-2xl border border-slate-800 bg-slate-900/60"><div class="border-b border-slate-800 px-6 py-4 text-sm font-semibold text-slate-200">Comentários ({{ comments.length }})</div><div v-if="!comments.length" class="px-6 py-5 text-sm text-slate-500">Nenhum comentário conhecido nesta cópia.</div><article v-for="comment in comments" :key="comment.hash" class="border-b border-slate-800/70 px-6 py-5 last:border-0"><div class="text-xs text-slate-500">{{ comment.autor_id }} · {{ formatDate(comment.criado_em) }}</div><p v-if="comment.tem_corpo && !comment.removido_localmente" class="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">{{ comment.corpo }}</p><p v-else class="mt-3 text-sm text-amber-300">Somente resumo disponível nesta cópia.</p><button v-if="!comment.proprio && !comment.removido_localmente && comment.tem_corpo" @click="changeLocalAvailability('/api/v1/content/remove-local', 'Remover o conteúdo local deste comentário? O cabeçalho será preservado.', comment.hash)" :disabled="isLoading" class="mt-3 text-xs text-amber-300 hover:text-amber-200">Remover conteúdo local</button><button v-else-if="!comment.proprio && comment.removido_localmente" @click="changeLocalAvailability('/api/v1/content/reimport', '', comment.hash)" :disabled="isLoading" class="mt-3 text-xs text-cyan-400 hover:text-cyan-300">Permitir nova importação</button></article></section>
      </template>
    </section>`,
    methods: {
        formatDate(value) { return value ? new Date(value).toLocaleString('pt-BR') : ''; },
        async load() {
            this.error = ''; this.item = null; this.comments = []; this.classification = null; this.editingClassification = false;
            try {
                const response = await fetch(`/api/v1/content/articles/${encodeURIComponent(this.itemHash)}`, { credentials: 'same-origin' });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.detail || 'Conteúdo indisponível.');
                this.item = data;
                if (data.tipo === 'ARTIGO') {
                    const [commentsResponse, classificationResponse] = await Promise.all([fetch(`/api/v1/content/articles/${encodeURIComponent(this.itemHash)}/comments`, { credentials: 'same-origin' }), fetch(`/api/v1/content/articles/${encodeURIComponent(this.itemHash)}/classification`, { credentials: 'same-origin' })]);
                    const commentsData = await commentsResponse.json().catch(() => ({}));
                    const classificationData = await classificationResponse.json().catch(() => ({}));
                    if (commentsResponse.ok) this.comments = commentsData.comentarios || [];
                    if (classificationResponse.ok) this.classification = classificationData;
                }
            } catch (error) { this.error = error.message; }
        },
        async changeLocalAvailability(path, confirmation = '', contentHash = this.itemHash) {
            if (confirmation && !window.confirm(confirmation)) return;
            this.message = ''; this.error = ''; this.isLoading = true;
            try {
                const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify({ content_hash: contentHash }) });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.detail || 'Não foi possível atualizar o conteúdo local.');
                this.message = data.status === 'REIMPORTACAO_HABILITADA' ? 'A próxima importação completa poderá restaurar o conteúdo.' : 'Conteúdo local removido; o cabeçalho foi preservado.';
                await this.load();
            } catch (error) { this.error = error.message; } finally { this.isLoading = false; }
        },
        startClassification() { this.editingClassification = !this.editingClassification; if (this.editingClassification && this.classification) { this.categoryInput = this.classification.categoria || ''; this.badgesInput = this.classification.badges.join(', '); } },
        async saveClassification() {
            this.message = ''; this.error = ''; this.isLoading = true;
            try {
                const badges = this.badgesInput.split(',').map((value) => value.trim()).filter(Boolean);
                const response = await fetch(`/api/v1/content/articles/${encodeURIComponent(this.itemHash)}/classification`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', body: JSON.stringify({ category: this.categoryInput.trim() || null, badges }) });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.detail || 'Não foi possível salvar a classificação local.');
                this.classification = data; this.editingClassification = false; this.message = 'Classificação salva somente nesta cópia.';
            } catch (error) { this.error = error.message; } finally { this.isLoading = false; }
        },
    },
};
