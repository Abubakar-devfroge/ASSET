// GSAP Animations for GridSet Home Page
// This script animates hero, features, enterprise, and AI sections for a modern feel
document.addEventListener('DOMContentLoaded', function() {
    // Animate Hero Section
    gsap.from('.section-title', {
        y: 60,
        opacity: 0,
        duration: 1.2,
        ease: 'power3.out',
        stagger: 0.2
    });
    gsap.from('.hero-img', {
        x: 80,
        opacity: 0,
        duration: 1.2,
        delay: 0.3,
        ease: 'power3.out'
    });
    // Animate Features Cards (Why Choose GridSet)
    gsap.from('.features-card', {
        y: 40,
        opacity: 0.01, // Use 0.01 instead of 0 to avoid display: none
        duration: 1,
        stagger: 0.15,
        delay: 0.7,
        ease: 'power2.out',
        clearProps: 'opacity,transform' // Ensure properties are cleared after animation
    });
    // Animate Enterprise Section
    gsap.from('.enterprise-img', {
        x: 80,
        opacity: 0,
        duration: 1.2,
        delay: 0.5,
        ease: 'power3.out'
    });
    // Animate AI Section
    gsap.from('.ai-img', {
        x: -80,
        opacity: 0,
        duration: 1.2,
        delay: 0.7,
        ease: 'power3.out'
    });
    gsap.from('.ai-btn', {
        scale: 0.8,
        opacity: 0.01, // Use 0.01 instead of 0
        duration: 0.7,
        delay: 1.1,
        stagger: 0.2,
        ease: 'back.out(1.7)',
        clearProps: 'opacity,transform'
    });
});
