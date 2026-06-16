/* ===================================================================
   AgrimIT — UI helpers (Fase 1)
   - Sidebar móvil + overlay
   - toast(msg) global
   - toggleModForm(id): desplegar mini-forms "Modificar"
   - cierre de modal por click en fondo
   - búsqueda global (debounce + fetch /search/), con guardas
   Reemplaza el JS inline del navbar viejo. Todo guardado contra
   elementos ausentes para no romper páginas sin esos componentes.
   =================================================================== */

(function () {
  'use strict'

  // ===== Sidebar móvil + overlay =====
  function initSidebar() {
    const sidebar = document.getElementById('sidebar')
    const overlay = document.getElementById('overlay')
    if (!sidebar || !overlay) return

    function openSide() {
      sidebar.classList.add('open')
      overlay.classList.add('show')
      document.body.style.overflow = 'hidden'
    }
    function closeSide() {
      sidebar.classList.remove('open')
      overlay.classList.remove('show')
      document.body.style.overflow = ''
    }

    document.querySelectorAll('.hamb').forEach((btn) =>
      btn.addEventListener('click', openSide)
    )
    overlay.addEventListener('click', closeSide)
    // Cerrar al navegar por un ítem del sidebar
    sidebar.querySelectorAll('.snav a').forEach((a) =>
      a.addEventListener('click', closeSide)
    )
    // Cerrar al pasar a desktop
    window.addEventListener('resize', function () {
      if (window.innerWidth > 860) closeSide()
    })
  }

  // ===== Toast global =====
  let toastTimer
  window.toast = function (msg) {
    const t = document.getElementById('toast')
    if (!t) return
    t.textContent = msg
    t.classList.add('show')
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => t.classList.remove('show'), 2200)
  }

  // ===== Mini-forms "Modificar" (project_template, Fase 2) =====
  // Alterna la visibilidad de un contenedor por id.
  window.toggleModForm = function (id) {
    const el = document.getElementById(id)
    if (!el) return
    el.style.display = el.style.display === 'none' || !el.style.display ? 'block' : 'none'
  }

  // ===== Modal: cerrar por click en el fondo =====
  function initModals() {
    document.querySelectorAll('.modal-bg').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('open')
      })
    })
  }

  // ===== Búsqueda global (portada del navbar viejo) =====
  function initSearch() {
    const searchInput = document.getElementById('search-input')
    if (!searchInput) return // páginas sin buscador: no-op

    const resultsContainer = document.getElementById('results-cont')
    const projectLink = document.getElementById('project-link')
    const searchWrap = searchInput.closest('.search')
    if (!resultsContainer || !projectLink) return
    const projectLinkUrl = projectLink.dataset.url
    const projectsUrl = searchWrap ? searchWrap.dataset.projectsUrl : null

    let searchTimeout
    let isSearchActive = false

    function clearResults() {
      resultsContainer.innerHTML = ''
      resultsContainer.classList.remove('show')
    }

    async function performSearch(query) {
      try {
        const response = await fetch(`/search/?query=${encodeURIComponent(query)}`)
        if (!response.ok) throw new Error('Search failed')
        const data = await response.json()
        if (data.results?.length) {
          isSearchActive = true
          displayResults(data.results)
        } else {
          isSearchActive = false
          clearResults()
        }
      } catch (error) {
        console.error('Search error:', error)
        isSearchActive = false
      }
    }

    function displayResults(results) {
      clearResults()
      const fragment = document.createDocumentFragment()
      results.forEach((result) => {
        const link = document.createElement('a')
        if (result.closed) link.className = 'closed-project'
        link.href = projectLinkUrl.replace('0', result.id)
        const titleSpan = document.createElement('span')
        titleSpan.textContent = result.type
        const dateSpan = document.createElement('span')
        dateSpan.textContent = result.datecreated
        dateSpan.classList.add('date-search')
        link.append(titleSpan, dateSpan)
        fragment.appendChild(link)
      })
      if (projectsUrl) {
        const seeMoreButton = document.createElement('button')
        seeMoreButton.className = 'search-button see-more'
        seeMoreButton.type = 'button'
        seeMoreButton.textContent = 'Ver más'
        seeMoreButton.onclick = () => {
          window.location = projectsUrl
        }
        fragment.appendChild(seeMoreButton)
      }
      resultsContainer.appendChild(fragment)
      resultsContainer.classList.add('show')
    }

    searchInput.addEventListener('keyup', () => {
      const query = searchInput.value.trim()
      if (!query) {
        clearResults()
        isSearchActive = false
        return
      }
      clearTimeout(searchTimeout)
      searchTimeout = setTimeout(() => {
        clearResults()
        performSearch(query)
      }, 300)
    })

    searchInput.addEventListener('click', () => {
      if (isSearchActive) resultsContainer.classList.add('show')
    })

    document.addEventListener('click', (event) => {
      if (!searchInput.contains(event.target) && !resultsContainer.contains(event.target)) {
        resultsContainer.classList.remove('show')
      }
    })
  }

  document.addEventListener('DOMContentLoaded', function () {
    initSidebar()
    initModals()
    initSearch()
  })
})()
