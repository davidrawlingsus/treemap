'use client'

import { useState } from 'react'
// TODO: Replace with your image component or use regular img tag
// import Image from 'next/image'
import { Dialog, DialogContent } from './ui/dialog'
import { Button } from './ui/button'
import { CheckCircle2 } from 'lucide-react'

interface StrategyCallModalProps {
  isOpen: boolean
  onClose: () => void
}

interface FormData {
  name: string
  email: string
  phone: string
  company: string
  websiteUrl: string
  preferredDate: string
  preferredTime: string
  additionalInfo: string
}

// TODO: Replace Image component if not using Next.js
// For regular img tag, use this wrapper:
const Image = ({ src, alt, fill, className, sizes }: any) => {
  if (fill) {
    return (
      <img
        src={src}
        alt={alt}
        className={className}
        style={{ objectFit: 'contain', width: '100%', height: '100%' }}
      />
    )
  }
  return <img src={src} alt={alt} className={className} />
}

export default function StrategyCallModal({ isOpen, onClose }: StrategyCallModalProps) {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    phone: '',
    company: '',
    websiteUrl: '',
    preferredDate: '',
    preferredTime: '',
    additionalInfo: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const clientLogos = [
    { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/katkin_logo_square.png', alt: 'KatKin' },
    { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/mous_logo_square.png', alt: 'Mous' },
    { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/hotjar_logo_square.png', alt: 'Hotjar' },
    { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/look_fabulous_forever_logo_square.png', alt: 'Look Fabulous Forever' },
    { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/wattbike_logo_rectangle.png', alt: 'Wattbike' },
    { src: 'https://neeuv3c4wu4qzcdw.public.blob.vercel-storage.com/logos/omlet_logo_square.png', alt: 'Omlet' },
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setSubmitError(null)

    try {
      // TODO: Update this URL to match your API endpoint
      const response = await fetch('/api/strategy-call', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        throw new Error('Failed to submit form')
      }

      setIsSubmitted(true)
    } catch (error) {
      console.error('Error submitting form:', error)
      setSubmitError('Something went wrong. Please try again or contact us directly at david@rawlings.us')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      onClose()
      // Reset form after a delay to allow the close animation to complete
      setTimeout(() => {
        setIsSubmitted(false)
        setFormData({
          name: '',
          email: '',
          phone: '',
          company: '',
          websiteUrl: '',
          preferredDate: '',
          preferredTime: '',
          additionalInfo: '',
        })
        setSubmitError(null)
      }, 300)
    }
  }

  const canSubmit = () => {
    return (
      formData.name.trim() !== '' &&
      formData.email.trim() !== '' &&
      formData.phone.trim() !== '' &&
      formData.preferredDate !== '' &&
      formData.preferredTime !== ''
    )
  }

  // Get today's date in YYYY-MM-DD format for min date
  const today = new Date().toISOString().split('T')[0]

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-white border-neutral-200 [&>button>svg]:!text-black">
        {isSubmitted ? (
          // Thank You Screen
          <div className="py-12 px-6 text-center">
            <div className="mb-8 inline-flex items-center justify-center w-20 h-20 rounded-full bg-[#B9F040]/20">
              <CheckCircle2 className="w-10 h-10 text-[#B9F040]" />
            </div>
            <h2 className="text-4xl font-bold mb-4 text-black">Thank You!</h2>
            <p className="text-lg text-neutral-700 mb-6 max-w-xl mx-auto">
              We&apos;ve received your booking request and will reach out shortly to confirm your strategy call.
            </p>
            <p className="text-neutral-600 mb-8">
              You&apos;ll receive a confirmation email at <span className="text-[#B9F040] font-semibold">{formData.email}</span>
            </p>
            <Button
              onClick={handleClose}
              className="bg-[#B9F040] text-black hover:bg-[#a0d636] px-8 py-6 text-base font-semibold"
            >
              Close
            </Button>
          </div>
        ) : (
          <div className="py-6">
            {/* Header Section */}
            <div className="mb-8 text-center">
              <h2 className="text-3xl md:text-4xl font-bold text-black mb-4">
                Book Your Free Strategy Call
              </h2>
              <p className="text-lg text-neutral-700 max-w-2xl mx-auto">
                Learn how Marketably&apos;s feedback driven system can grow your profitability.
              </p>
            </div>

            {/* Social Proof - Logo Grid */}
            <div className="mb-8 pb-8 border-b border-neutral-200">
              <p className="text-sm text-neutral-600 text-center mb-4 uppercase tracking-wide">
                Trusted by Industry Leaders
              </p>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-6 items-center">
                {clientLogos.map((logo, index) => (
                  <div
                    key={index}
                    className="relative h-12 w-full grayscale opacity-60 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
                  >
                    <Image
                      src={logo.src}
                      alt={logo.alt}
                      fill
                      className="object-contain"
                      sizes="100px"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Personal Information */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium mb-2 text-black">
                    Full Name *
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="John Smith"
                    className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-2 text-black">
                    Email Address *
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="john@company.com"
                    className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="phone" className="block text-sm font-medium mb-2 text-black">
                    Phone Number *
                  </label>
                  <input
                    id="phone"
                    type="tel"
                    required
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+1 (555) 123-4567"
                    className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label htmlFor="company" className="block text-sm font-medium mb-2 text-black">
                    Company Name
                  </label>
                  <input
                    id="company"
                    type="text"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    placeholder="Your Company"
                    className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="websiteUrl" className="block text-sm font-medium mb-2 text-black">
                  Website URL
                </label>
                <input
                  id="websiteUrl"
                  type="text"
                  value={formData.websiteUrl}
                  onChange={(e) => setFormData({ ...formData, websiteUrl: e.target.value })}
                  placeholder="example.com"
                  className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors"
                />
              </div>

              {/* Date and Time Selection */}
              <div className="border-t border-neutral-200 pt-6">
                <h3 className="text-black font-semibold mb-4">Select Your Preferred Time</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="preferredDate" className="block text-sm font-medium mb-2 text-black">
                      Preferred Date *
                    </label>
                    <input
                      id="preferredDate"
                      type="date"
                      required
                      min={today}
                      value={formData.preferredDate}
                      onChange={(e) => setFormData({ ...formData, preferredDate: e.target.value })}
                      className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black focus:border-[#B9F040] focus:outline-none transition-colors"
                    />
                  </div>
                  <div>
                    <label htmlFor="preferredTime" className="block text-sm font-medium mb-2 text-black">
                      Preferred Time *
                    </label>
                    <select
                      id="preferredTime"
                      required
                      value={formData.preferredTime}
                      onChange={(e) => setFormData({ ...formData, preferredTime: e.target.value })}
                      className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black focus:border-[#B9F040] focus:outline-none transition-colors"
                    >
                      <option value="">Select a time...</option>
                      <option value="09:00">9:00 AM</option>
                      <option value="10:00">10:00 AM</option>
                      <option value="11:00">11:00 AM</option>
                      <option value="12:00">12:00 PM</option>
                      <option value="13:00">1:00 PM</option>
                      <option value="14:00">2:00 PM</option>
                      <option value="15:00">3:00 PM</option>
                      <option value="16:00">4:00 PM</option>
                      <option value="17:00">5:00 PM</option>
                    </select>
                  </div>
                </div>
                <p className="text-neutral-600 text-sm mt-2">
                  * Times are in your local timezone. We&apos;ll confirm availability and send a calendar invite.
                </p>
              </div>

              {/* Additional Information */}
              <div>
                <label htmlFor="additionalInfo" className="block text-sm font-medium mb-2 text-black">
                  What would you like to discuss? (Optional)
                </label>
                <textarea
                  id="additionalInfo"
                  value={formData.additionalInfo}
                  onChange={(e) => setFormData({ ...formData, additionalInfo: e.target.value })}
                  placeholder="Tell us about your goals, challenges, or what you'd like to achieve..."
                  rows={4}
                  className="w-full px-4 py-3 text-base bg-white border-2 border-neutral-300 rounded-lg text-black placeholder:text-neutral-400 focus:border-[#B9F040] focus:outline-none transition-colors resize-none"
                />
              </div>

              {/* Error Message */}
              {submitError && (
                <div className="p-4 bg-red-50 border border-red-300 rounded-lg text-red-700 text-sm">
                  {submitError}
                </div>
              )}

              {/* Submit Button */}
              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-6 py-3 text-neutral-600 hover:text-black transition-colors"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <Button
                  type="submit"
                  disabled={!canSubmit() || isSubmitting}
                  className="bg-[#B9F040] text-black hover:bg-[#a0d636] px-8 py-6 text-base font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Submitting...
                    </>
                  ) : (
                    'Book Strategy Call'
                  )}
                </Button>
              </div>
            </form>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

