import { LandingPageData } from '@/types/landing/landing';

export const landingDataEn: LandingPageData = {
  nav: {
    logo: 'InsightFlow',
    links: [
      { label: 'Home', href: '#' },
      { label: 'Dashboard', href: '#' },
      { label: 'Features', href: '#' },
      { label: 'Insights', href: '#' },
      { label: 'About', href: '#' },
    ],
    loginText: 'Login',
    signUpText: 'Sign Up',
  },
  hero: {
    titleLine1: "Turn Business Data",
    titleLine2: 'Into Better',
    titleLine3: 'Decisions.',
    description: "Analyze your business performance, uncover hidden trends, and turn raw data into actionable insights from one intelligent platform without manually analyzing spreadsheets.",
    primaryButtonText: 'Explore Dashboard',
    primaryButtonHref: '/en/login',
    secondaryButtonText: 'See How It Works',
    heroImage: '/images/hero1.png',
    heroImageAlt: 'Business Analytics Graphic',
    //demoVideoUrl: '/video.mp4',
  },
  sponsors: {
    title: 'Designed for modern business data workflows',
    sponsors: [
      { name: 'CSV Data Parsing' },
      { name: 'Automated KPIs' },
      { name: 'Profit Tracking' },
      { name: 'Trend Analysis' }
    ],
  },
  support: {
    title: 'How our platform simplifies business analytics',
    description: 'A lightweight analytics solution built for small and medium-sized businesses to understand sales, profit margins, and revenue performance without complexity.',
    features: [
      {
        title: 'Fast Processing',
        description: 'Upload your CSV sales data and instantly process records with automated validation and zero setup.',
        iconName: 'activity',
      },
      {
        title: 'Smart Analytics',
        description: 'Automatically calculate total revenue, profit margins, average order value, and product trends.',
        iconName: 'pie-chart',
      },
      {
        title: 'Actionable Insights',
        description: 'Receive automatically generated rule-based recommendations based on your actual sales metrics.',
        iconName: 'command',
      },
    ],
  },
  features: {
    title: 'Everything you need to grow',
    description: 'We offer a variety of intelligent features that help you increase productivity and understand your sales data without the spreadsheet hassle.',
    buttonText: 'Get Started',
    cards: [
      {
        title: 'Business Overview',
        description: 'Get a bird\'s-eye view of your total revenue, orders, customers, and profit margins in one dashboard.',
        imageType: 'collaboration',
      },
      {
        title: 'Simple Data Upload',
        description: 'Upload your business data securely. We validate your records and parse everything instantly.',
        imageType: 'cloud',
      },
      {
        title: 'Automated Insights',
        description: 'We provide clear, rule-based insights and regional performance metrics tailored to your dataset.',
        imageType: 'analytics',
      },
    ],
  },
  testimonial: {
    title: 'Built for Effortless Decision Making',
    subtitle: 'Everything you need to transform raw business spreadsheets into clear, actionable decisions.',
    quote: 'Stop spending hours fixing spreadsheet formulas and manually calculating profit margins. Upload your sales data and immediately uncover your top-performing products and growth opportunities.',
    author: '— Intelligent Business Analytics Engine',
    avatars: [
      'https://i.pravatar.cc/100?img=11',
      'https://i.pravatar.cc/100?img=12',
      'https://i.pravatar.cc/100?img=13',
      'https://i.pravatar.cc/100?img=14',
    ],
  },
  ctaForm: {
    title: 'Get Started Now',
    emailLabel: 'Email',
    emailPlaceholder: 'Enter your email',
    messageLabel: 'Message',
    messagePlaceholder: 'How can we help your business?',
    buttonText: 'Request Access',
    altText: 'or View Live Demo',
  },
  footer: {
    logo: 'InsightFlow',
    description: 'Turn your raw sales data into actionable business insights today.',
    emailPlaceholder: 'Enter your email here',
    copyright: '© 2026 InsightFlow Inc. Copyright and rights reserved',
    linkGroups: [
      {
        title: 'Platform',
        links: [
          { label: 'Dashboard', href: '#' },
          { label: 'Analytics', href: '#' },
          { label: 'Data Upload', href: '#' },
          { label: 'Insights', href: '#' },
        ],
      },
      {
        title: 'Resources',
        links: [
          { label: 'Help Center', href: '#' },
          { label: 'Documentation', href: '#' },
          { label: 'Sample Data', href: '#' },
          { label: 'API Status', href: '#' },
        ],
      },
      {
        title: 'Company',
        links: [
          { label: 'About Us', href: '#' },
          { label: 'Security', href: '#' },
          { label: 'Terms of Service', href: '#' },
          { label: 'Pricing', href: '#' },
        ],
      },
    ],
    bottomLinks: [
      { label: 'Terms and Conditions', href: '#' },
      { label: 'Privacy Policy', href: '#' },
    ],
  },
};
