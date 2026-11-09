export interface NavItem {
  label: string;
  href: string;
}

export interface NavData {
  logo: string;
  links: NavItem[];
  loginText: string;
  signUpText: string;
}

export interface HeroData {
  titleLine1: string;
  titleLine2: string;
  titleLine3: string;
  description: string;
  primaryButtonText: string;
  primaryButtonHref?: string;
  secondaryButtonText: string;
  heroImage: string;
  heroImageAlt: string;
  demoVideoUrl?: string;
}

export interface Sponsor {
  name: string;
}

export interface SponsorsData {
  title: string;
  sponsors: Sponsor[];
}

export interface Rating {
  score: number;
  maxScore: number;
  company: string;
}

export interface StatItem {
  value: string;
  label: string;
  sublabel: string;
}

export interface SupportFeature {
  title: string;
  description: string;
  iconName: string;
}

export interface SupportData {
  title: string;
  description: string;
  ratings?: Rating[];
  stats?: StatItem[];
  features: SupportFeature[];
}

export interface FeatureCard {
  title: string;
  description: string;
  imageType: string;
}

export interface FeaturesData {
  title: string;
  description: string;
  buttonText: string;
  cards: FeatureCard[];
}

export interface TestimonialData {
  title: string;
  subtitle: string;
  quote: string;
  author: string;
  avatars: string[];
}

export interface CtaFormData {
  title: string;
  emailLabel: string;
  emailPlaceholder: string;
  messageLabel: string;
  messagePlaceholder: string;
  buttonText: string;
  altText: string;
}

export interface FooterLinkGroup {
  title: string;
  links: NavItem[];
}

export interface FooterData {
  logo: string;
  description: string;
  emailPlaceholder: string;
  copyright: string;
  linkGroups: FooterLinkGroup[];
  bottomLinks: NavItem[];
}

export interface LandingPageData {
  nav: NavData;
  hero: HeroData;
  sponsors: SponsorsData;
  support: SupportData;
  features: FeaturesData;
  testimonial: TestimonialData;
  ctaForm: CtaFormData;
  footer: FooterData;
}
