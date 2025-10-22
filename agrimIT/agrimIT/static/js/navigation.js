/*
===========================================
AGRIMITE - RESPONSIVE NAVIGATION SCRIPT
===========================================
JavaScript para el menú hamburger responsive
Autor: AgrimIT Team
Fecha: 2025
===========================================
*/

document.addEventListener('DOMContentLoaded', function() {
    // ===========================================
    // VARIABLES DEL MENÚ
    // ===========================================
    
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const navList = document.getElementById('nav-list');
    const navOverlay = document.getElementById('nav-overlay');
    const body = document.body;
    
    // ===========================================
    // FUNCIONES PRINCIPALES
    // ===========================================
    
    /**
     * Alternar estado del menú móvil
     */
    function toggleMenu() {
        const isActive = navList.classList.contains('active');
        
        if (isActive) {
            closeMenu();
        } else {
            openMenu();
        }
    }
    
    /**
     * Abrir menú móvil
     */
    function openMenu() {
        hamburgerBtn.classList.add('active');
        navList.classList.add('active');
        navOverlay.classList.add('active');
        body.style.overflow = 'hidden';
        
        // Accessibility
        hamburgerBtn.setAttribute('aria-expanded', 'true');
        navList.setAttribute('aria-hidden', 'false');
    }
    
    /**
     * Cerrar menú móvil
     */
    function closeMenu() {
        hamburgerBtn.classList.remove('active');
        navList.classList.remove('active');
        navOverlay.classList.remove('active');
        body.style.overflow = '';
        
        // Cerrar todos los submenús
        closeAllSubmenus();
        
        // Accessibility
        hamburgerBtn.setAttribute('aria-expanded', 'false');
        navList.setAttribute('aria-hidden', 'true');
    }
    
    /**
     * Cerrar todos los submenús
     */
    function closeAllSubmenus() {
        document.querySelectorAll('.navbar-submenu.show').forEach(submenu => {
            submenu.classList.remove('show');
        });
    }
    
    /**
     * Alternar submenú en móvil
     */
    function toggleSubmenu(submenuId) {
        const submenu = document.getElementById(submenuId);
        if (submenu) {
            const isShow = submenu.classList.contains('show');
            
            // Cerrar otros submenús
            closeAllSubmenus();
            
            // Alternar el submenú actual
            if (!isShow) {
                submenu.classList.add('show');
            }
        }
    }
    
    /**
     * Verificar si estamos en vista móvil
     */
    function isMobileView() {
        return window.innerWidth <= 768;
    }
    
    // ===========================================
    // EVENT LISTENERS
    // ===========================================
    
    // Botón hamburger
    if (hamburgerBtn) {
        hamburgerBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleMenu();
        });
        
        // Accessibility: Enter y Space
        hamburgerBtn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleMenu();
            }
        });
    } else {
        console.error('❌ Hamburger button not found!');
    }
    
    // Overlay para cerrar menú
    if (navOverlay) {
        navOverlay.addEventListener('click', closeMenu);
    }
    
    // Enlaces de navegación
    document.querySelectorAll('.nav-dropdown a').forEach(link => {
        link.addEventListener('click', function(e) {
            const submenuId = this.getAttribute('data-submenu');
            
            if (submenuId && isMobileView()) {
                // En móvil, si tiene submenú, alternar submenú
                e.preventDefault();
                toggleSubmenu(submenuId);
            } else if (!submenuId && isMobileView()) {
                // En móvil, si no tiene submenú, cerrar menú después de un breve delay
                setTimeout(closeMenu, 150);
            }
        });
    });
    
    // Manejo de hover en desktop
    document.querySelectorAll('.nav-dropdown li').forEach(item => {
        const submenu = item.querySelector('.navbar-submenu');
        
        if (submenu) {
            // Mouse enter
            item.addEventListener('mouseenter', function() {
                if (!isMobileView()) {
                    closeAllSubmenus();
                    submenu.classList.add('show');
                }
            });
            
            // Mouse leave
            item.addEventListener('mouseleave', function() {
                if (!isMobileView()) {
                    submenu.classList.remove('show');
                }
            });
        }
    });
    
    // ===========================================
    // EVENTOS GLOBALES
    // ===========================================
    
    // Redimensionar ventana
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            if (!isMobileView()) {
                closeMenu();
            }
        }, 100);
    });
    
    // Tecla Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (navList.classList.contains('active')) {
                closeMenu();
            }
        }
    });
    
    // Click fuera del menú
    document.addEventListener('click', function(e) {
        if (isMobileView() && 
            navList.classList.contains('active') && 
            !navList.contains(e.target) && 
            !hamburgerBtn.contains(e.target)) {
            closeMenu();
        }
    });
    
    // ===========================================
    // INICIALIZACIÓN
    // ===========================================
    
    // Configurar atributos de accesibilidad iniciales
    if (hamburgerBtn) {
        hamburgerBtn.setAttribute('aria-expanded', 'false');
        hamburgerBtn.setAttribute('aria-controls', 'nav-list');
    }
    
    if (navList) {
        navList.setAttribute('aria-hidden', 'true');
    }
    
    // ===========================================
    // UTILIDADES ADICIONALES
    // ===========================================
    
    /**
     * Smooth scroll para enlaces internos
     */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            
            if (target) {
                // Cerrar menú móvil si está abierto
                if (isMobileView() && navList.classList.contains('active')) {
                    closeMenu();
                }
                
                // Scroll suave
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    /**
     * Optimización: Debounce para eventos de scroll
     */
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(function() {
            // Cerrar submenús al hacer scroll en desktop
            if (!isMobileView()) {
                closeAllSubmenus();
            }
        }, 150);
    });
    
    // ===========================================
    // EXPOSER FUNCIONES GLOBALES (opcional)
    // ===========================================
    
    // Hacer funciones disponibles globalmente si es necesario
    window.AgrimITNavigation = {
        openMenu: openMenu,
        closeMenu: closeMenu,
        toggleMenu: toggleMenu,
        isMobileView: isMobileView
    };
    
    // Log de inicialización (solo en desarrollo)
    // Navigation system initialized
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        // Debug mode: navigation initialized
    }
});

/*
===========================================
FUNCIONES DE SOPORTE PARA OTROS SCRIPTS
===========================================
*/

/**
 * Función helper para otros scripts que necesiten saber si el menú está abierto
 */
function isNavigationOpen() {
    const navList = document.getElementById('nav-list');
    return navList ? navList.classList.contains('active') : false;
}

/**
 * Función helper para cerrar navegación desde otros scripts
 */
function closeNavigation() {
    if (window.AgrimITNavigation) {
        window.AgrimITNavigation.closeMenu();
    }
}
