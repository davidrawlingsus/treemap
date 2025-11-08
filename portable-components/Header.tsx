'use client'

import { useState, useEffect } from 'react'
// TODO: Replace with your router's Link component
// import Link from 'next/link'
// import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'
import StrategyCallModal from './StrategyCallModal'

// Navigation items configuration
const NAV_ITEMS = [
  { id: 'clients', label: 'Clients', hash: '#clients' },
  { id: 'impact', label: 'Results', hash: '#impact' },
  { id: 'process', label: 'Process', hash: '#process' },
  { id: 'backstory', label: 'Backstory', hash: '#backstory' },
  { id: 'people', label: 'People', hash: '#people' },
  { id: 'pricing', label: 'Pricing', path: '/challenge' },
] as const

// TODO: Replace this with your router's Link component
// For React Router: import { Link } from 'react-router-dom'
// For other routers, adapt accordingly
const Link = ({ href, children, className, onClick, ...props }: any) => {
  return (
    <a href={href} className={className} onClick={onClick} {...props}>
      {children}
    </a>
  )
}

// TODO: Replace this with your router's pathname hook
// For React Router: import { useLocation } from 'react-router-dom'
// const usePathname = () => {
//   const location = useLocation()
//   return location.pathname
// }
const usePathname = () => {
  if (typeof window !== 'undefined') {
    return window.location.pathname
  }
  return '/'
}

export default function Header() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<string | null>(null)
  const pathname = usePathname()

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen)
  }

  const openStrategyCallModal = () => {
    setIsModalOpen(true)
    setIsMobileMenuOpen(false) // Close mobile menu if open
  }

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false)
  }

  // Helper to determine if we need to navigate to home page first
  const getNavLink = (hash: string) => {
    return pathname === '/' ? hash : `/${hash}`
  }

  // Scroll spy - track which section is in view
  useEffect(() => {
    // Only run on home page
    if (pathname !== '/') {
      setActiveSection(null)
      return
    }

    const observerOptions = {
      root: null,
      rootMargin: '-20% 0px -60% 0px', // Trigger when section is roughly centered
      threshold: 0,
    }

    const observerCallback = (entries: IntersectionObserverEntry[]) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveSection(entry.target.id)
        }
      })
    }

    const observer = new IntersectionObserver(observerCallback, observerOptions)

    // Observe all sections
    const sections = ['clients', 'impact', 'process', 'backstory', 'people'].map(id => 
      document.getElementById(id)
    ).filter(Boolean) as HTMLElement[]

    sections.forEach(section => observer.observe(section))

    return () => observer.disconnect()
  }, [pathname])

  const isNavItemActive = (item: typeof NAV_ITEMS[number]) => {
    // For pricing, check if we're on the challenge page
    if (item.id === 'pricing') {
      return pathname === '/challenge'
    }
    // For hash sections, check if section is active
    return activeSection === item.id
  }

  return (
    <nav className="sticky top-0 z-50 bg-black px-4 lg:px-8 py-4 border-b border-neutral-800/50">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo */}
        <div className="flex flex-col">
          <Link href="/" className="font-bold text-3xl font-[family-name:var(--font-lato)] hover:opacity-80 transition-opacity">
            <span className="text-white">market</span>
            <span className="text-[#B9F040]">ably</span>
          </Link>
          <span className="text-xs text-[#B9F040] tracking-wide mt-1">Feedback-Fueled Marketing</span>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden lg:flex items-center space-x-8">
          {/* Navigation Links */}
          <div className="flex items-center space-x-8">
            {NAV_ITEMS.map((item) => {
              const isActive = isNavItemActive(item)
              const href = 'path' in item ? item.path : getNavLink(item.hash)
              
              return (
                <Link
                  key={item.id}
                  href={href}
                  className={`relative text-white hover:text-[#B9F040] cursor-pointer transition-colors ${
                    isActive ? 'text-[#B9F040] font-semibold' : ''
                  }`}
                >
                  {item.label}
                  {isActive && (
                    <span 
                      className="absolute -bottom-[6px] left-0 right-0 h-[2px] bg-[#B9F040]"
                      aria-hidden="true"
                    />
                  )}
                </Link>
              )
            })}
          </div>

          {/* CTA Buttons */}
          <div className="flex items-center gap-4 ml-8">
            <Link href="/challenge" className="border-2 border-white text-white px-6 py-2 rounded-lg font-semibold text-sm uppercase hover:bg-white hover:text-[#1A2B3C] transition-colors">
              LANDING PAGE CHALLENGE
            </Link>
            <button 
              onClick={openStrategyCallModal}
              className="bg-[#B9F040] text-black px-6 py-2 rounded-lg font-semibold text-sm uppercase hover:bg-[#a0d636] transition-colors"
            >
              BOOK A STRATEGY CALL
            </button>
          </div>
        </div>

        {/* Mobile Menu Button */}
        <div className="lg:hidden">
          <button
            onClick={toggleMobileMenu}
            className="text-[#B9F040] hover:text-white transition-colors"
            aria-label="Toggle mobile menu"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="lg:hidden mt-4 pb-4">
          <div className="flex flex-col space-y-4">
            {NAV_ITEMS.map((item) => {
              const isActive = isNavItemActive(item)
              const href = 'path' in item ? item.path : getNavLink(item.hash)
              
              return (
                <Link
                  key={item.id}
                  href={href}
                  onClick={closeMobileMenu}
                  className={`text-white hover:text-[#B9F040] cursor-pointer transition-colors ${
                    isActive ? 'text-[#B9F040] font-semibold' : ''
                  }`}
                >
                  {item.label}
                </Link>
              )
            })}
            
            {/* Mobile CTA Buttons */}
            <div className="pt-4 flex flex-col gap-3">
              <Link href="/challenge" onClick={closeMobileMenu} className="border-2 border-white text-white px-6 py-3 rounded-lg font-semibold text-sm uppercase hover:bg-white hover:text-[#1A2B3C] transition-colors block text-center">
                LANDING PAGE CHALLENGE
              </Link>
              <button 
                onClick={openStrategyCallModal}
                className="bg-[#B9F040] text-black px-6 py-3 rounded-lg font-semibold text-sm uppercase hover:bg-[#a0d636] transition-colors block text-center w-full"
              >
                BOOK A STRATEGY CALL
              </button>
            </div>

            {/* Testimonial */}
            <div className="pt-6 mt-6 border-t border-white/20">
              <blockquote className="text-white/90 text-base italic mb-3">
                &ldquo;Paid for itself a thousand times over.&rdquo;
              </blockquote>
              <p className="text-white/70 text-sm">
                <span className="font-semibold">Elliott Fox</span> &mdash; Wattbike
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Strategy Call Modal */}
      <StrategyCallModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </nav>
  )
}

