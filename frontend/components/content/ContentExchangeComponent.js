export default {
  name: "ContentExchangeComponent",
  emits: ["open-item", "copy-revoked"],
  data() {
    return {
      message: "",
      error: "",
      isLoading: false,
      items: [],
      since: "",
      unexportedOnly: false,
      categoryFilter: "",
      authorFilter: "",
      search: "",
      publicationScope: "TODAS",
      sortOrder: "RECENTES",
      mobileFiltersOpen: false,
      calendarOpen: false,
      selectedSince: "",
      calendarMonth: new Date(
        new Date().getFullYear(),
        new Date().getMonth(),
        1,
      ),
      expandedArticleHash: "",
      articleComments: {},
      commentsLoading: "",
      commentErrors: {},
    };
  },
  computed: {
    articles() {
      return this.items.filter((item) => item.tipo === "ARTIGO");
    },
    categories() {
      return [
        ...new Set(this.articles.map((item) => item.categoria).filter(Boolean)),
      ].sort((a, b) => a.localeCompare(b, "pt-BR"));
    },
    authors() {
      return [
        ...new Set(
          this.articles
            .map((item) => item.autor_pseudonimo || item.autor_id)
            .filter(Boolean),
        ),
      ].sort((a, b) => a.localeCompare(b, "pt-BR"));
    },
    filteredArticles() {
      const term = this.search.trim().toLocaleLowerCase("pt-BR");
      const sinceDate = this.since ? new Date(`${this.since}T00:00:00`) : null;
      return this.articles
        .filter((item) => {
          const author = item.autor_pseudonimo || item.autor_id;
          const scope =
            this.publicationScope === "TODAS" ||
            (this.publicationScope === "MINHAS" ? item.proprio : !item.proprio);
          const text =
            !term ||
            [item.titulo, item.categoria, author, ...(item.badges || [])]
              .filter(Boolean)
              .some((value) => value.toLocaleLowerCase("pt-BR").includes(term));
          return (
            scope &&
            (!this.categoryFilter || item.categoria === this.categoryFilter) &&
            (!this.authorFilter || author === this.authorFilter) &&
            text &&
            (!sinceDate || new Date(item.criado_em) >= sinceDate)
          );
        })
        .sort((a, b) =>
          this.sortOrder === "ANTIGOS"
            ? new Date(a.criado_em) - new Date(b.criado_em)
            : new Date(b.criado_em) - new Date(a.criado_em),
        );
    },
    calendarTitle() {
      return this.calendarMonth.toLocaleDateString("pt-BR", {
        month: "long",
        year: "numeric",
      });
    },
    calendarWeeks() {
      const first = new Date(
        this.calendarMonth.getFullYear(),
        this.calendarMonth.getMonth(),
        1,
      );
      const start = new Date(first);
      start.setDate(first.getDate() - first.getDay());
      return Array.from({ length: 42 }, (_, index) => {
        const date = new Date(start);
        date.setDate(start.getDate() + index);
        return {
          date,
          iso: this.dateToIso(date),
          currentMonth: date.getMonth() === this.calendarMonth.getMonth(),
        };
      });
    },
  },
  mounted() {
    this.loadLibrary();
  },
  template: `<section class="space-y-5 text-left">
      <header class="flex flex-col gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-start sm:justify-between"><div><h2 class="text-xl font-bold text-slate-100">Acervo</h2><p class="mt-1 text-sm text-slate-400">Encontre, organize e compartilhe as publicações desta cópia.</p></div><div class="grid grid-cols-2 gap-2 sm:flex"><button @click="request('/api/v1/content/imports')" :disabled="isLoading" class="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-100 hover:bg-slate-700 disabled:opacity-50">Importar ARKX</button><button @click="exportContent" :disabled="isLoading" class="rounded-xl bg-cyan-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-cyan-600 disabled:opacity-50">Exportar</button></div></header>
      <button @click="mobileFiltersOpen=!mobileFiltersOpen" class="flex w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm text-slate-200 hover:bg-slate-800 lg:hidden"><span>Filtros e ordenação</span><span>{{ mobileFiltersOpen ? '▲' : '▼' }}</span></button>
      <div class="grid gap-5 lg:grid-cols-[15rem_minmax(0,1fr)]"><aside :class="mobileFiltersOpen ? 'block' : 'hidden'" class="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 lg:block"><div class="flex items-center justify-between"><h3 class="text-sm font-semibold text-slate-100">Filtrar acervo</h3><button v-if="mobileFiltersOpen" @click="mobileFiltersOpen=false" class="text-xs text-slate-400 hover:text-slate-200 lg:hidden">Fechar</button></div><label class="mt-4 block text-xs text-slate-400">Buscar<input v-model="search" type="search" placeholder="Título ou marcador" class="mt-1 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"></label><div class="mt-5"><div class="mb-2 text-xs text-slate-400">Publicações</div><div class="space-y-1"><button v-for="scope in [{value:'TODAS',label:'Todos'},{value:'MINHAS',label:'Minhas publicações'},{value:'OUTRAS',label:'Outras publicações'}]" :key="scope.value" @click="publicationScope=scope.value" :class="publicationScope === scope.value ? 'border-cyan-800/80 bg-cyan-950/50 text-cyan-200' : 'border-transparent text-slate-300 hover:bg-slate-800'" class="flex w-full items-center justify-between rounded-lg border px-2.5 py-2 text-left text-sm"><span>{{ scope.label }}</span><span class="text-xs text-slate-500">{{ scope.value === 'TODAS' ? articles.length : scope.value === 'MINHAS' ? articles.filter(item => item.proprio).length : articles.filter(item => !item.proprio).length }}</span></button></div></div><label v-if="categories.length" class="mt-5 block text-xs text-slate-400">Categoria<select v-model="categoryFilter" class="mt-1 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"><option value="">Todas</option><option v-for="category in categories" :key="category" :value="category">{{ category }}</option></select></label><label class="mt-5 block text-xs text-slate-400">Autor<select v-model="authorFilter" class="mt-1 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"><option value="">Todos</option><option v-for="author in authors" :key="author" :value="author">{{ author }}</option></select></label><div class="mt-5 text-xs text-slate-400">Publicados a partir de<button @click="openCalendar" class="mt-1 flex w-full items-center justify-between rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-left text-sm text-slate-100"><span>{{ since ? formatDateOnly(since) : 'Qualquer data' }}</span><span>📅</span></button></div><label class="mt-5 block text-xs text-slate-400">Ordenação<select v-model="sortOrder" class="mt-1 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"><option value="RECENTES">Mais recentes</option><option value="ANTIGOS">Mais antigos</option></select></label><div class="mt-5 border-t border-slate-800 pt-4"><div class="text-xs font-medium text-slate-300">Na próxima exportação</div><label class="mt-3 flex items-start gap-2 text-xs text-slate-400"><input v-model="unexportedOnly" type="checkbox" :disabled="isLoading" class="mt-0.5 h-4 w-4 accent-cyan-600">Incluir somente itens ainda não exportados</label><p class="mt-2 text-[11px] leading-4 text-slate-500">Esta opção define o conteúdo do próximo arquivo. Ela não filtra a lista do Acervo e o registro é apenas local.</p></div></aside>
      <main><div class="mb-3 flex items-center justify-between gap-3"><h3 class="text-sm font-semibold text-slate-200">Artigos recentes</h3><span class="text-xs text-slate-500">{{ filteredArticles.length }} {{ filteredArticles.length === 1 ? 'resultado' : 'resultados' }}</span></div><div v-if="filteredArticles.length" class="space-y-3"><template v-for="item in filteredArticles" :key="item.hash"><article :class="item.tem_corpo && !item.removido_localmente ? 'border-l-emerald-400' : 'border-l-amber-400'" class="overflow-hidden rounded-2xl border border-l-4 border-slate-800 bg-slate-900/60"><div class="flex items-start justify-between gap-4 p-4"><div class="min-w-0 flex-1"><button @click="$emit('open-item',item.hash)" class="block max-w-full truncate text-left text-sm font-semibold text-slate-100 hover:text-cyan-300">{{ item.titulo || 'Sem título' }}<span v-if="item.proprio" class="ml-2 inline-block rounded-full border border-cyan-800/70 px-2 py-0.5 align-middle text-[10px] font-medium text-cyan-300">Sua publicação</span></button><div class="mt-2 flex flex-wrap gap-x-1.5 gap-y-1 text-xs text-slate-400"><span>{{ item.categoria || 'Sem categoria' }}</span><span>·</span><span>{{ item.autor_pseudonimo || item.autor_id }}</span><span>·</span><span>{{ formatRelativeDate(item.criado_em) }}</span><span>·</span><button @click.stop="toggleComments(item.hash)" :aria-expanded="expandedArticleHash === item.hash" class="text-cyan-300 underline decoration-cyan-800 underline-offset-2 hover:text-cyan-200">{{ item.comentarios }} {{ item.comentarios === 1 ? 'comentário' : 'comentários' }}</button></div><div v-if="item.badges.length" class="mt-3 flex flex-wrap gap-1.5"><span v-for="badge in item.badges" :key="badge" class="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300">{{ badge }}</span></div><button v-if="item.comentarios" @click.stop="toggleComments(item.hash)" :aria-expanded="expandedArticleHash === item.hash" class="mt-3 rounded-lg bg-slate-800 px-2.5 py-1.5 text-xs text-cyan-300 hover:bg-slate-700">{{ expandedArticleHash === item.hash ? 'Ocultar comentários' : 'Exibir comentários' }}</button></div><div class="shrink-0 text-right"><span :class="item.tem_corpo && !item.removido_localmente ? 'text-emerald-300' : 'text-amber-300'" class="block text-xs font-medium">{{ item.tem_corpo && !item.removido_localmente ? '● Completo' : '◐ Resumo' }}</span><span v-if="item.proprio" :class="item.exportado ? 'text-cyan-400' : 'text-slate-500'" class="mt-1 block text-[11px]">{{ item.exportado ? 'Exportado' : 'Não exportado' }}</span></div></div><section v-if="expandedArticleHash === item.hash" class="mx-4 mb-4 max-h-48 overflow-y-auto border-l-2 border-cyan-800/70 bg-slate-950/50 px-4"><div v-if="commentsLoading === item.hash" class="py-4 text-sm text-slate-400">Carregando comentários…</div><p v-else-if="commentErrors[item.hash]" class="py-4 text-sm text-red-300">{{ commentErrors[item.hash] }}</p><template v-else><article v-for="comment in articleComments[item.hash] || []" :key="comment.hash" class="border-b border-slate-800 py-3 last:border-0"><div class="text-xs text-slate-500">{{ comment.autor_pseudonimo || comment.autor_id }} · {{ formatRelativeDate(comment.criado_em) }}</div><p v-if="comment.tem_corpo && !comment.removido_localmente" class="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">{{ comment.corpo }}</p><p v-else class="mt-2 text-sm text-amber-300">Somente resumo disponível nesta cópia.</p></article><p v-if="!(articleComments[item.hash] || []).length" class="py-4 text-sm text-slate-500">Nenhum comentário conhecido nesta cópia.</p></template></section></article></template></div><p v-else-if="articles.length" class="rounded-xl border border-dashed border-slate-800 p-5 text-sm text-slate-500">Nenhum artigo corresponde aos filtros locais.</p><p v-else class="rounded-xl border border-dashed border-slate-800 p-5 text-sm text-slate-500">O acervo local ainda não possui artigos publicados.</p></main></div>
      <div v-if="calendarOpen" class="fixed inset-0 z-20 flex items-center justify-center bg-slate-950/70 p-4" @click.self="calendarOpen=false"><div class="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-xl"><div class="flex items-center justify-between gap-3"><button @click="changeMonth(-1)" aria-label="Mês anterior" class="rounded-lg px-2 py-1 text-slate-300 hover:bg-slate-800">←</button><h3 class="capitalize text-base font-semibold text-slate-100">{{ calendarTitle }}</h3><button @click="changeMonth(1)" aria-label="Próximo mês" class="rounded-lg px-2 py-1 text-slate-300 hover:bg-slate-800">→</button></div><div class="mt-5 grid grid-cols-7 gap-1 text-center text-xs text-slate-500"><span v-for="weekday in ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb']" :key="weekday" class="py-1">{{ weekday }}</span></div><div class="grid grid-cols-7 gap-1"><button v-for="day in calendarWeeks" :key="day.iso" @click="selectDay(day)" :class="[day.currentMonth ? 'text-slate-100' : 'text-slate-600', selectedSince === day.iso ? 'bg-cyan-700 text-white hover:bg-cyan-600' : 'hover:bg-slate-800']" class="aspect-square rounded-lg text-sm transition-colors">{{ day.date.getDate() }}</button></div><div class="mt-5 flex items-center justify-between gap-2"><button @click="clearCalendar" class="rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-slate-800">Limpar filtro</button><div class="flex gap-2"><button @click="calendarOpen=false" class="rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancelar</button><button @click="applyCalendar" class="rounded-xl bg-cyan-700 px-3 py-2 text-sm font-medium text-white hover:bg-cyan-600">Aplicar</button></div></div></div></div><p v-if="message" class="text-sm text-emerald-400">{{ message }}</p><p v-if="error" class="text-sm text-red-300">{{ error }}</p></section>`,
  methods: {
    dateToIso(date) {
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    },
    formatDateOnly(value) {
      return value
        ? new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR")
        : "";
    },
    formatRelativeDate(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const target = new Date(date);
      target.setHours(0, 0, 0, 0);
      const days = Math.round((today - target) / 86400000);
      if (days === 0) return "hoje";
      if (days === 1) return "ontem";
      if (days > 1 && days < 7) return `há ${days} dias`;
      return date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
        year:
          date.getFullYear() === today.getFullYear() ? undefined : "numeric",
      });
    },
    openCalendar() {
      this.selectedSince = this.since;
      const source = this.since
        ? new Date(`${this.since}T00:00:00`)
        : new Date();
      this.calendarMonth = new Date(source.getFullYear(), source.getMonth(), 1);
      this.calendarOpen = true;
    },
    changeMonth(offset) {
      this.calendarMonth = new Date(
        this.calendarMonth.getFullYear(),
        this.calendarMonth.getMonth() + offset,
        1,
      );
    },
    selectDay(day) {
      this.selectedSince = day.iso;
      this.calendarMonth = new Date(
        day.date.getFullYear(),
        day.date.getMonth(),
        1,
      );
    },
    clearCalendar() {
      this.selectedSince = "";
    },
    applyCalendar() {
      this.since = this.selectedSince;
      this.calendarOpen = false;
    },
    async loadLibrary() {
      try {
        const response = await fetch("/api/v1/content/library", {
          credentials: "same-origin",
        });
        const data = await response.json().catch(() => ({}));
        if (response.ok) {
          this.items = data.itens || [];
        }
      } catch (_) {}
    },
    async toggleComments(articleHash) {
      if (this.expandedArticleHash === articleHash) {
        this.expandedArticleHash = "";
        return;
      }
      this.expandedArticleHash = articleHash;
      if (this.articleComments[articleHash]) return;
      this.commentsLoading = articleHash;
      this.commentErrors = { ...this.commentErrors, [articleHash]: "" };
      try {
        const response = await fetch(
          `/api/v1/content/articles/${encodeURIComponent(articleHash)}/comments`,
          { credentials: "same-origin" },
        );
        const data = await response.json().catch(() => ({}));
        if (!response.ok)
          throw new Error(
            data.detail || "Não foi possível carregar os comentários.",
          );
        this.articleComments = {
          ...this.articleComments,
          [articleHash]: data.comentarios || [],
        };
      } catch (error) {
        this.commentErrors = {
          ...this.commentErrors,
          [articleHash]: error.message,
        };
      } finally {
        this.commentsLoading = "";
      }
    },
    exportContent() {
      return this.request("/api/v1/content/exports/COMPLETA", {
        since: this.since || null,
        unexported_only: this.unexportedOnly,
      });
    },
    async request(path, body = {}) {
      this.error = "";
      this.message = "";
      this.isLoading = true;
      try {
        const response = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(body),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "Ação não concluída.");
        if (data.status === "COPIA_REVOGADA") {
          window.alert(
            "Esta cópia foi revogada. O estado foi aplicado e o conteúdo do arquivo não foi importado.",
          );
          this.$emit("copy-revoked");
          return;
        }
        this.message = data.antecessores_indisponiveis
          ? `Importação concluída. ${data.antecessores_indisponiveis} versão(ões) permanece(m) sem predecessor local.`
          : data.status ||
            `Importação concluída: ${data.aceitos || 0} item(ns) aceito(s).`;
        await this.loadLibrary();
      } catch (error) {
        this.error = error.message;
      } finally {
        this.isLoading = false;
      }
    },
  },
};
