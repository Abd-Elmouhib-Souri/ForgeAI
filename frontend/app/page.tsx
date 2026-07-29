'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

type Lang = 'fr' | 'en';
type AgentColor = 'blue' | 'yellow' | 'pink' | 'violet' | 'red';

const content = {
  fr: {
    nav: {
      modules: 'Modules',
      workflow: 'Workflow',
      audience: 'Utilisateurs',
      agents: 'Agents IA',
      login: 'Connexion',
      start: 'Commencer',
    },
    hero: {
      badge: 'From Idea to Startup, Powered by AI',
      title1: 'Transformez une idée floue en',
      title2: 'plan startup prêt à présenter',
      description:
        'ForgeAI analyse votre idée comme une équipe de consultants, product managers, architectes logiciels et mentors startup. En quelques minutes, obtenez une étude de marché, un Business Model Canvas, une analyse SWOT, un score startup, un backlog Agile, une architecture technique et des livrables exportables.',
      primary: 'Analyser mon idée gratuitement',
      secondary: 'Accéder à mon espace',
      trust1: '6 modules fonctionnels',
      trust2: '5 agents IA principaux',
      trust3: '10+ livrables générés',
    },
    dashboard: {
      score: 'Startup Score',
      potential: 'Fort potentiel',
      preview: 'Aperçu du rapport IA',
      projectLabel: 'Projet analysé',
      projectName: 'Application e-santé intelligente',
      generated: 'Analyse générée',
      confidence: 'Confiance',
      confidenceValue: 'Élevée',
      innovation: 'Innovation',
      feasibility: 'Faisabilité',
      profitability: 'Rentabilité',
      scalability: 'Scalabilité',
      market: 'Étude de marché',
      swot: 'SWOT + BMC',
      backlog: 'Backlog Scrum',
      architecture: 'Architecture technique',
      exports: 'Exports',
      ready: 'Prêt',
      completed: 'Terminé',
      pdf: 'PDF',
      word: 'Word',
      ppt: 'Pitch Deck',
    },
    strip: [
      'Innovation Hub',
      'Startup Evaluator',
      'AI Project Manager',
      'Solution Architect',
      'Document Generator',
      'Dashboard & Analytics',
    ],
    featuresHeader: {
      label: 'Plateforme complète',
      title: 'Tout ce qu’il faut pour tester, structurer et présenter un projet',
      text:
        'ForgeAI ne donne pas seulement une opinion. Il produit une analyse exploitable, structurée et exportable pour passer plus vite de l’idée à l’exécution.',
    },
    features: [
      {
        icon: '💡',
        title: "Analyse intelligente de l'idée",
        text:
          "ForgeAI comprend votre idée, détecte le secteur, identifie le problème réel, la cible et génère un Innovation Score clair.",
      },
      {
        icon: '📈',
        title: 'Startup Evaluator complet',
        text:
          'Étude de marché, SWOT, Business Model Canvas, analyse concurrentielle, estimation financière et Startup Score multi-critères.',
      },
      {
        icon: '🧠',
        title: 'Débat IA stratégique',
        text:
          'Un Defender défend votre idée, un Critic la challenge comme un investisseur sceptique, puis un Judge donne un verdict final.',
      },
      {
        icon: '🕵️',
        title: 'ForgeCrawler concurrentiel',
        text:
          'Recherche web et scraping pour comparer votre projet à de vrais concurrents, pas seulement à des réponses inventées par l’IA.',
      },
      {
        icon: '🧩',
        title: 'AI Project Manager',
        text:
          'Génération automatique du Product Backlog, Epics, User Stories, priorités MoSCoW, Story Points et Sprint Planning.',
      },
      {
        icon: '🏗️',
        title: 'Solution Architect',
        text:
          'Recommandation de stack technique, architecture logicielle, schéma de base de données et diagrammes UML adaptés au projet.',
      },
      {
        icon: '👥',
        title: 'Persona Builder',
        text:
          'Création de profils clients réalistes avec objectifs, frustrations, budget, canaux d’acquisition et parcours utilisateur.',
      },
      {
        icon: '📄',
        title: 'Exports professionnels',
        text:
          'Générez des livrables prêts à partager : Business Plan PDF, rapport Word éditable et Pitch Deck PowerPoint.',
      },
    ],
    workflow: {
      label: 'Workflow intelligent',
      title: 'Un chemin clair de l’idée au livrable final',
      text:
        'L’utilisateur décrit son idée, ForgeAI orchestre les agents IA, sauvegarde les résultats et génère des documents prêts pour la démo, la soutenance ou la présentation client.',
      steps: [
        {
          number: '01',
          title: 'Décrivez votre idée',
          text: 'Titre, description, secteur, problème, cible, région et langue de sortie.',
        },
        {
          number: '02',
          title: 'Analyse business automatique',
          text: 'Innovation Score, technologies recommandées, améliorations et risques initiaux.',
        },
        {
          number: '03',
          title: 'Évaluation stratégique',
          text: 'Marché, SWOT, BMC, concurrence, finances, personas et Startup Score.',
        },
        {
          number: '04',
          title: 'Plan projet + architecture',
          text: 'Backlog Scrum, sprints, Story Points, stack technique, UML et schéma DB.',
        },
        {
          number: '05',
          title: 'Exports professionnels',
          text: 'PDF, Word, Pitch Deck PowerPoint et livrables adaptés au profil utilisateur.',
        },
      ],
    },
    audience: {
      label: 'Pour qui ?',
      title: 'Une plateforme pour tous les créateurs de valeur',
      text:
        'ForgeAI adapte l’analyse et les livrables selon le profil : entrepreneur, étudiant, consultant, incubateur ou équipe projet.',
      users: [
        {
          title: 'Entrepreneurs',
          text:
            'Validez une idée, structurez votre business model et préparez un dossier crédible pour partenaires ou investisseurs.',
        },
        {
          title: 'Étudiants / PFE',
          text:
            'Transformez un sujet de projet en cahier des charges, backlog, architecture, UML et rapport académique structuré.',
        },
        {
          title: 'Consultants',
          text:
            'Produisez rapidement des analyses clients, rapports multi-projets et livrables professionnels personnalisables.',
        },
        {
          title: 'Incubateurs & PME',
          text:
            'Évaluez plusieurs idées, comparez les risques, suivez les versions et accélérez la préparation des projets.',
        },
      ],
    },
    agents: {
      label: 'Agents IA',
      title: 'Une équipe virtuelle pour challenger votre projet',
      text:
        'Chaque agent joue un rôle précis : analyser, structurer, planifier, concevoir, challenger et transformer les résultats en actions.',
      list: [
        {
          name: 'AI Business Analyst',
          detail: 'Analyse idée, marché, SWOT, BMC et score.',
          color: 'blue',
        },
        {
          name: 'AI Product Owner',
          detail: 'Génère Epics, Features et User Stories.',
          color: 'yellow',
        },
        {
          name: 'AI Scrum Master',
          detail: 'Planifie les sprints et les Story Points.',
          color: 'pink',
        },
        {
          name: 'AI Solution Architect',
          detail: 'Crée architecture, stack, UML et DB.',
          color: 'violet',
        },
        {
          name: 'AI Startup Mentor',
          detail: 'Donne conseils, risques et recommandations.',
          color: 'red',
        },
        {
          name: 'Fact Checker',
          detail: 'Vérifie la cohérence et les points non sourcés.',
          color: 'blue',
        },
      ],
    },
    results: {
      label: 'Résultat attendu',
      title: 'Votre business plan, votre roadmap et votre architecture générés en quelques minutes.',
      text:
        'ForgeAI génère un dossier complet : analyse de l’idée, étude de marché, SWOT, Business Model Canvas, analyse concurrentielle, estimation financière, Startup Score, personas clients, Product Backlog, Sprint Planning, stack technique, diagrammes UML, rapport PDF, document Word et Pitch Deck PowerPoint.',
      cta: 'Créer mon premier projet',
    },
    footer: 'DotJcom ForgeAI — From Idea to Startup, Powered by AI.',
  },
  en: {
    nav: {
      modules: 'Modules',
      workflow: 'Workflow',
      audience: 'Users',
      agents: 'AI Agents',
      login: 'Login',
      start: 'Get Started',
    },
    hero: {
      badge: 'From Idea to Startup, Powered by AI',
      title1: 'Turn a raw idea into a',
      title2: 'startup plan ready to present',
      description:
        'ForgeAI analyzes your idea like a team of consultants, product managers, software architects and startup mentors. In minutes, get a market study, Business Model Canvas, SWOT analysis, startup score, Agile backlog, technical architecture and exportable deliverables.',
      primary: 'Analyze my idea for free',
      secondary: 'Open my workspace',
      trust1: '6 functional modules',
      trust2: '5 core AI agents',
      trust3: '10+ generated deliverables',
    },
    dashboard: {
      score: 'Startup Score',
      potential: 'High potential',
      preview: 'AI report preview',
      projectLabel: 'Analyzed project',
      projectName: 'Smart healthtech application',
      generated: 'Analysis generated',
      confidence: 'Confidence',
      confidenceValue: 'High',
      innovation: 'Innovation',
      feasibility: 'Feasibility',
      profitability: 'Profitability',
      scalability: 'Scalability',
      market: 'Market study',
      swot: 'SWOT + BMC',
      backlog: 'Scrum backlog',
      architecture: 'Technical architecture',
      exports: 'Exports',
      ready: 'Ready',
      completed: 'Done',
      pdf: 'PDF',
      word: 'Word',
      ppt: 'Pitch Deck',
    },
    strip: [
      'Innovation Hub',
      'Startup Evaluator',
      'AI Project Manager',
      'Solution Architect',
      'Document Generator',
      'Dashboard & Analytics',
    ],
    featuresHeader: {
      label: 'Complete platform',
      title: 'Everything you need to test, structure and present a project',
      text:
        'ForgeAI does not only give an opinion. It produces usable, structured and exportable analysis to move faster from idea to execution.',
    },
    features: [
      {
        icon: '💡',
        title: 'Smart idea analysis',
        text:
          'ForgeAI understands your idea, detects the sector, identifies the real problem, the target users and generates a clear Innovation Score.',
      },
      {
        icon: '📈',
        title: 'Complete Startup Evaluator',
        text:
          'Market study, SWOT, Business Model Canvas, competitive analysis, financial estimation and multi-criteria Startup Score.',
      },
      {
        icon: '🧠',
        title: 'Strategic AI Debate',
        text:
          'A Defender supports your idea, a Critic challenges it like a skeptical investor, then a Judge gives a final verdict.',
      },
      {
        icon: '🕵️',
        title: 'Competitive ForgeCrawler',
        text:
          'Web search and scraping to compare your project with real competitors, not only AI-invented answers.',
      },
      {
        icon: '🧩',
        title: 'AI Project Manager',
        text:
          'Automatic Product Backlog generation, Epics, User Stories, MoSCoW priorities, Story Points and Sprint Planning.',
      },
      {
        icon: '🏗️',
        title: 'Solution Architect',
        text:
          'Technical stack recommendation, software architecture, database schema and UML diagrams adapted to your project.',
      },
      {
        icon: '👥',
        title: 'Persona Builder',
        text:
          'Creates realistic customer profiles with goals, frustrations, budget, acquisition channels and user journeys.',
      },
      {
        icon: '📄',
        title: 'Professional exports',
        text:
          'Generate ready-to-share deliverables: PDF Business Plan, editable Word report and PowerPoint Pitch Deck.',
      },
    ],
    workflow: {
      label: 'Smart workflow',
      title: 'A clear path from idea to final deliverable',
      text:
        'The user describes an idea, ForgeAI orchestrates AI agents, saves results and generates documents ready for demos, academic defense or client presentations.',
      steps: [
        {
          number: '01',
          title: 'Describe your idea',
          text: 'Title, description, sector, problem, target users, region and output language.',
        },
        {
          number: '02',
          title: 'Automatic business analysis',
          text: 'Innovation Score, recommended technologies, improvements and initial risks.',
        },
        {
          number: '03',
          title: 'Strategic evaluation',
          text: 'Market, SWOT, BMC, competition, finance, personas and Startup Score.',
        },
        {
          number: '04',
          title: 'Project plan + architecture',
          text: 'Scrum backlog, sprints, Story Points, technical stack, UML and database schema.',
        },
        {
          number: '05',
          title: 'Professional exports',
          text: 'PDF, Word, PowerPoint Pitch Deck and deliverables adapted to the user profile.',
        },
      ],
    },
    audience: {
      label: 'Who is it for?',
      title: 'A platform for every value creator',
      text:
        'ForgeAI adapts the analysis and deliverables to the user profile: entrepreneur, student, consultant, incubator or project team.',
      users: [
        {
          title: 'Entrepreneurs',
          text:
            'Validate an idea, structure your business model and prepare a credible file for partners or investors.',
        },
        {
          title: 'Students / Final Projects',
          text:
            'Turn a project topic into specifications, backlog, architecture, UML and a structured academic report.',
        },
        {
          title: 'Consultants',
          text:
            'Produce client analyses, multi-project reports and professional customizable deliverables faster.',
        },
        {
          title: 'Incubators & SMEs',
          text:
            'Evaluate multiple ideas, compare risks, track versions and accelerate project preparation.',
        },
      ],
    },
    agents: {
      label: 'AI Agents',
      title: 'A virtual team to challenge your project',
      text:
        'Each agent has a precise role: analyze, structure, plan, design, challenge and turn results into actions.',
      list: [
        {
          name: 'AI Business Analyst',
          detail: 'Analyzes idea, market, SWOT, BMC and score.',
          color: 'blue',
        },
        {
          name: 'AI Product Owner',
          detail: 'Generates Epics, Features and User Stories.',
          color: 'yellow',
        },
        {
          name: 'AI Scrum Master',
          detail: 'Plans sprints and estimates Story Points.',
          color: 'pink',
        },
        {
          name: 'AI Solution Architect',
          detail: 'Creates architecture, stack, UML and DB.',
          color: 'violet',
        },
        {
          name: 'AI Startup Mentor',
          detail: 'Gives advice, risks and recommendations.',
          color: 'red',
        },
        {
          name: 'Fact Checker',
          detail: 'Checks consistency and unsourced points.',
          color: 'blue',
        },
      ],
    },
    results: {
      label: 'Expected result',
      title: 'Your business plan, roadmap and architecture generated in minutes.',
      text:
        'ForgeAI generates a complete file: idea analysis, market study, SWOT, Business Model Canvas, competitive analysis, financial estimation, Startup Score, customer personas, Product Backlog, Sprint Planning, technical stack, UML diagrams, PDF report, Word document and PowerPoint Pitch Deck.',
      cta: 'Create my first project',
    },
    footer: 'DotJcom ForgeAI — From Idea to Startup, Powered by AI.',
  },
};

export default function WelcomePage() {
  const [lang, setLang] = useState<Lang>('fr');

  const t = useMemo(() => content[lang], [lang]);

  return (
    <main className="welcome-page">
      <nav className="navbar">
        <Link href="/" className="brand">
          <span className="brand-icon">✦</span>
          <span>ForgeAI</span>
        </Link>

        <div className="nav-links">
          <a href="#features">{t.nav.modules}</a>
          <a href="#workflow">{t.nav.workflow}</a>
          <a href="#audience">{t.nav.audience}</a>
          <a href="#agents">{t.nav.agents}</a>

          <div className="language-switch" aria-label="Language selector">
            <button
              type="button"
              className={lang === 'fr' ? 'active' : ''}
              onClick={() => setLang('fr')}
            >
              FR
            </button>
            <button
              type="button"
              className={lang === 'en' ? 'active' : ''}
              onClick={() => setLang('en')}
            >
              EN
            </button>
          </div>

          <Link href="/login" className="nav-login">
            {t.nav.login}
          </Link>

          <Link href="/register" className="nav-button">
            {t.nav.start}
          </Link>
        </div>
      </nav>

      <section className="hero">
        <div className="blur blur-blue" />
        <div className="blur blur-pink" />
        <div className="blur blur-yellow" />

        <div className="hero-content">
          <div className="badge">
            <span>🚀</span>
            {t.hero.badge}
          </div>

          <h1>
            {t.hero.title1}
            <span>{t.hero.title2}</span>
          </h1>

          <p className="hero-description">{t.hero.description}</p>

          <div className="hero-actions">
            <Link href="/register" className="primary-button">
              {t.hero.primary}
            </Link>

            <Link href="/login" className="secondary-button">
              {t.hero.secondary}
            </Link>
          </div>

          <div className="trust-row">
            <span>{t.hero.trust1}</span>
            <span>{t.hero.trust2}</span>
            <span>{t.hero.trust3}</span>
          </div>
        </div>

        <div className="hero-dashboard">
          <div className="window-header">
            <div className="window-dots">
              <span className="dot red" />
              <span className="dot yellow" />
              <span className="dot green" />
            </div>
            <span className="preview-label">{t.dashboard.preview}</span>
          </div>

          <div className="project-preview">
            <div>
              <span>{t.dashboard.projectLabel}</span>
              <strong>{t.dashboard.projectName}</strong>
            </div>
            <div className="status-pill">{t.dashboard.generated}</div>
          </div>

          <div className="score-card">
            <div>
              <span>{t.dashboard.score}</span>
              <strong>84%</strong>
            </div>
            <div className="score-pill">{t.dashboard.potential}</div>
          </div>

          <div className="metrics-grid">
            <Metric label={t.dashboard.innovation} value="9/10" />
            <Metric label={t.dashboard.feasibility} value="8/10" />
            <Metric label={t.dashboard.profitability} value="8/10" />
            <Metric label={t.dashboard.scalability} value="9/10" />
          </div>

          <div className="report-list">
            <ReportItem label={t.dashboard.market} value={t.dashboard.completed} />
            <ReportItem label={t.dashboard.swot} value={t.dashboard.completed} />
            <ReportItem label={t.dashboard.backlog} value={t.dashboard.ready} />
            <ReportItem label={t.dashboard.architecture} value={t.dashboard.ready} />
          </div>

          <div className="export-row">
            <span>{t.dashboard.exports}</span>
            <div>
              <strong>{t.dashboard.pdf}</strong>
              <strong>{t.dashboard.word}</strong>
              <strong>{t.dashboard.ppt}</strong>
            </div>
          </div>

          <div className="confidence-row">
            <span>{t.dashboard.confidence}</span>
            <strong>{t.dashboard.confidenceValue}</strong>
          </div>
        </div>
      </section>

      <section className="modules-strip">
        {t.strip.map((module) => (
          <span key={module}>{module}</span>
        ))}
      </section>

      <section id="features" className="section">
        <div className="section-header">
          <span className="section-label">{t.featuresHeader.label}</span>
          <h2>{t.featuresHeader.title}</h2>
          <p>{t.featuresHeader.text}</p>
        </div>

        <div className="features-grid">
          {t.features.map((feature) => (
            <div className="feature-card" key={feature.title}>
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="workflow" className="workflow-section">
        <div className="workflow-card">
          <div className="section-header left">
            <span className="section-label">{t.workflow.label}</span>
            <h2>{t.workflow.title}</h2>
            <p>{t.workflow.text}</p>
          </div>

          <div className="timeline">
            {t.workflow.steps.map((step) => (
              <Step
                key={step.number}
                number={step.number}
                title={step.title}
                text={step.text}
              />
            ))}
          </div>
        </div>
      </section>

      <section id="audience" className="section">
        <div className="section-header">
          <span className="section-label">{t.audience.label}</span>
          <h2>{t.audience.title}</h2>
          <p>{t.audience.text}</p>
        </div>

        <div className="audience-grid">
          {t.audience.users.map((user) => (
            <div className="audience-card" key={user.title}>
              <h3>{user.title}</h3>
              <p>{user.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="agents" className="agents-section">
        <div className="agents-card">
          <div className="section-header left">
            <span className="section-label">{t.agents.label}</span>
            <h2>{t.agents.title}</h2>
            <p>{t.agents.text}</p>
          </div>

          <div className="agents-grid">
            {t.agents.list.map((agent) => (
              <Agent
                key={agent.name}
                name={agent.name}
                detail={agent.detail}
                color={agent.color as AgentColor}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="results-section">
        <div className="result-box">
          <span>{t.results.label}</span>
          <h2>{t.results.title}</h2>
          <p>{t.results.text}</p>
          <Link href="/register" className="primary-button">
            {t.results.cta}
          </Link>
        </div>
      </section>

      <footer className="footer">
        <div className="brand footer-brand">
          <span className="brand-icon">✦</span>
          <span>ForgeAI</span>
        </div>
        <p>{t.footer}</p>
      </footer>

      <style jsx>{`
        .welcome-page {
          min-height: 100vh;
          background:
            radial-gradient(circle at 12% 8%, rgba(125, 211, 252, 0.55), transparent 28%),
            radial-gradient(circle at 85% 16%, rgba(244, 114, 182, 0.42), transparent 30%),
            radial-gradient(circle at 50% 38%, rgba(253, 224, 71, 0.24), transparent 26%),
            linear-gradient(135deg, #f8fbff 0%, #fff7fb 48%, #fffdf2 100%);
          color: #15182f;
          overflow-x: hidden;
        }

        .navbar {
          width: min(1180px, calc(100% - 32px));
          margin: 0 auto;
          padding: 24px 0;
          display: flex;
          align-items: center;
          justify-content: space-between;
          position: relative;
          z-index: 10;
        }

        .brand {
          display: flex;
          align-items: center;
          gap: 10px;
          color: #111827;
          text-decoration: none;
          font-weight: 950;
          letter-spacing: -0.05em;
          font-size: 24px;
        }

        .brand-icon {
          width: 38px;
          height: 38px;
          display: grid;
          place-items: center;
          border-radius: 15px;
          color: white;
          background: linear-gradient(135deg, #38bdf8, #8b5cf6, #fb7185);
          box-shadow: 0 18px 40px rgba(139, 92, 246, 0.25);
        }

        .nav-links {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 9px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.76);
          border: 1px solid rgba(148, 163, 184, 0.24);
          box-shadow: 0 18px 50px rgba(15, 23, 42, 0.06);
          backdrop-filter: blur(18px);
        }

        .nav-links a {
          color: #475569;
          text-decoration: none;
          font-size: 14px;
          font-weight: 850;
          transition: 0.2s;
        }

        .nav-links a:hover {
          color: #7c3aed;
        }

        .language-switch {
          display: flex;
          align-items: center;
          padding: 4px;
          border-radius: 999px;
          background: #f1f5f9;
          border: 1px solid rgba(148, 163, 184, 0.28);
        }

        .language-switch button {
          border: 0;
          cursor: pointer;
          padding: 7px 10px;
          border-radius: 999px;
          color: #64748b;
          background: transparent;
          font-size: 12px;
          font-weight: 950;
          transition: 0.2s ease;
        }

        .language-switch button.active {
          color: white;
          background: linear-gradient(135deg, #38bdf8, #8b5cf6, #fb7185);
          box-shadow: 0 10px 20px rgba(139, 92, 246, 0.22);
        }

        .nav-login {
          padding-left: 4px;
        }

        .nav-button {
          color: white !important;
          padding: 12px 18px;
          border-radius: 999px;
          background: #111827;
          box-shadow: 0 14px 30px rgba(17, 24, 39, 0.2);
        }

        .hero {
          width: min(1180px, calc(100% - 32px));
          margin: 0 auto;
          position: relative;
          display: grid;
          grid-template-columns: 1.05fr 0.95fr;
          gap: 54px;
          align-items: center;
          padding: 58px 0 62px;
          min-height: 680px;
        }

        .blur {
          position: absolute;
          border-radius: 999px;
          filter: blur(28px);
          opacity: 0.7;
          z-index: 1;
        }

        .blur-blue {
          width: 190px;
          height: 190px;
          background: #7dd3fc;
          top: 88px;
          left: -70px;
        }

        .blur-pink {
          width: 230px;
          height: 230px;
          background: #f0abfc;
          top: 40px;
          right: -80px;
        }

        .blur-yellow {
          width: 180px;
          height: 180px;
          background: #fde047;
          bottom: 60px;
          left: 42%;
        }

        .hero-content,
        .hero-dashboard {
          position: relative;
          z-index: 2;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 10px 16px;
          border-radius: 999px;
          color: #334155;
          font-weight: 900;
          background: rgba(255, 255, 255, 0.76);
          border: 1px solid rgba(148, 163, 184, 0.24);
          box-shadow: 0 16px 44px rgba(15, 23, 42, 0.06);
          margin-bottom: 24px;
        }

        h1 {
          margin: 0;
          color: #0f172a;
          font-size: clamp(46px, 7vw, 86px);
          line-height: 0.92;
          letter-spacing: -0.08em;
        }

        h1 span {
          display: block;
          background: linear-gradient(90deg, #0284c7, #7c3aed, #db2777, #f59e0b);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        }

        .hero-description {
          max-width: 720px;
          margin: 28px 0 0;
          color: #475569;
          font-size: 18.5px;
          line-height: 1.82;
          font-weight: 600;
        }

        .hero-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 16px;
          margin-top: 34px;
        }

        .primary-button,
        .secondary-button {
          min-height: 56px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 0 24px;
          border-radius: 18px;
          text-decoration: none;
          font-weight: 950;
          transition: 0.22s ease;
        }

        .primary-button {
          color: white;
          background: linear-gradient(135deg, #38bdf8, #8b5cf6, #fb7185);
          box-shadow: 0 20px 48px rgba(139, 92, 246, 0.3);
        }

        .primary-button:hover,
        .secondary-button:hover {
          transform: translateY(-3px);
        }

        .secondary-button {
          color: #172033;
          background: rgba(255, 255, 255, 0.78);
          border: 1px solid rgba(148, 163, 184, 0.28);
        }

        .trust-row {
          margin-top: 36px;
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }

        .trust-row span {
          padding: 12px 15px;
          border-radius: 16px;
          color: #334155;
          background: rgba(255, 255, 255, 0.75);
          border: 1px solid rgba(148, 163, 184, 0.2);
          box-shadow: 0 14px 38px rgba(15, 23, 42, 0.055);
          font-weight: 900;
          font-size: 13px;
        }

        .hero-dashboard {
          padding: 24px;
          border-radius: 36px;
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 247, 252, 0.82)),
            radial-gradient(circle at top right, rgba(240, 171, 252, 0.32), transparent 36%);
          border: 1px solid rgba(255, 255, 255, 0.82);
          box-shadow:
            0 34px 90px rgba(15, 23, 42, 0.14),
            inset 0 1px 0 rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(22px);
          transform: rotate(2deg);
        }

        .window-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          margin-bottom: 18px;
        }

        .window-dots {
          display: flex;
          gap: 8px;
        }

        .dot {
          width: 13px;
          height: 13px;
          border-radius: 50%;
        }

        .red {
          background: #fb7185;
        }

        .yellow {
          background: #facc15;
        }

        .green {
          background: #4ade80;
        }

        .preview-label {
          color: #64748b;
          font-size: 12px;
          font-weight: 950;
          padding: 8px 12px;
          border-radius: 999px;
          background: rgba(241, 245, 249, 0.85);
          border: 1px solid rgba(148, 163, 184, 0.22);
        }

        .project-preview {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 16px;
          margin-bottom: 14px;
          border-radius: 22px;
          background: rgba(248, 250, 252, 0.82);
          border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .project-preview span {
          display: block;
          color: #64748b;
          font-size: 12px;
          font-weight: 900;
        }

        .project-preview strong {
          display: block;
          margin-top: 5px;
          color: #0f172a;
          font-size: 15px;
          line-height: 1.25;
        }

        .status-pill {
          flex: 0 0 auto;
          padding: 9px 12px;
          border-radius: 999px;
          color: #166534;
          background: #dcfce7;
          font-size: 12px;
          font-weight: 950;
          border: 1px solid rgba(34, 197, 94, 0.18);
        }

        .score-card {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 18px;
          padding: 26px;
          border-radius: 30px;
          color: white;
          background: linear-gradient(135deg, #0ea5e9, #6366f1, #d946ef, #ec4899);
          box-shadow: 0 22px 55px rgba(14, 165, 233, 0.25);
        }

        .score-card span {
          display: block;
          font-weight: 850;
          opacity: 0.92;
        }

        .score-card strong {
          display: block;
          margin-top: 6px;
          font-size: 66px;
          line-height: 1;
          letter-spacing: -0.08em;
        }

        .score-pill {
          padding: 9px 12px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.2);
          font-size: 12px;
          font-weight: 950;
          white-space: nowrap;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
          margin: 18px 0;
        }

        .metric {
          padding: 15px;
          border-radius: 20px;
          background: rgba(248, 250, 252, 0.88);
          border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .metric span {
          display: block;
          color: #64748b;
          font-size: 12px;
          font-weight: 900;
        }

        .metric strong {
          display: block;
          margin-top: 6px;
          color: #111827;
          font-size: 24px;
          letter-spacing: -0.04em;
        }

        .report-list {
          display: grid;
          gap: 10px;
        }

        .report-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          padding: 13px 15px;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.86);
          border: 1px solid rgba(148, 163, 184, 0.16);
        }

        .report-item div {
          display: flex;
          align-items: center;
          gap: 10px;
          min-width: 0;
        }

        .report-item span {
          color: #334155;
          font-size: 14px;
          font-weight: 850;
        }

        .report-item strong {
          flex: 0 0 auto;
          color: #16a34a;
          font-size: 13px;
          font-weight: 950;
        }

        .report-check {
          width: 24px;
          height: 24px;
          display: grid;
          place-items: center;
          border-radius: 50%;
          color: #16a34a !important;
          background: #dcfce7;
          font-size: 13px !important;
          font-weight: 950 !important;
        }

        .export-row,
        .confidence-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          margin-top: 12px;
          padding: 14px 15px;
          border-radius: 18px;
          background: rgba(248, 250, 252, 0.86);
          border: 1px solid rgba(148, 163, 184, 0.16);
        }

        .export-row > span,
        .confidence-row span {
          color: #64748b;
          font-size: 13px;
          font-weight: 950;
        }

        .export-row div {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 8px;
        }

        .export-row strong,
        .confidence-row strong {
          padding: 7px 10px;
          border-radius: 999px;
          color: #7c3aed;
          background: rgba(139, 92, 246, 0.1);
          font-size: 12px;
          font-weight: 950;
        }

        .modules-strip {
          width: min(1180px, calc(100% - 32px));
          margin: 0 auto 22px;
          padding: 18px;
          display: flex;
          gap: 12px;
          overflow-x: auto;
          border-radius: 28px;
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(148, 163, 184, 0.2);
          box-shadow: 0 20px 60px rgba(15, 23, 42, 0.05);
        }

        .modules-strip span {
          flex: 0 0 auto;
          padding: 12px 16px;
          border-radius: 999px;
          background: linear-gradient(135deg, #e0f2fe, #fce7f3);
          color: #334155;
          font-weight: 950;
          font-size: 13px;
        }

        .section {
          width: min(1180px, calc(100% - 32px));
          margin: 0 auto;
          padding: 82px 0;
        }

        .section-header {
          max-width: 790px;
          margin: 0 auto 42px;
          text-align: center;
        }

        .section-header.left {
          text-align: left;
          margin: 0;
        }

        .section-label {
          display: inline-flex;
          margin-bottom: 14px;
          padding: 9px 15px;
          border-radius: 999px;
          color: #7c3aed;
          background: rgba(139, 92, 246, 0.1);
          border: 1px solid rgba(139, 92, 246, 0.16);
          font-weight: 950;
          font-size: 13px;
        }

        .section-header h2,
        .result-box h2 {
          margin: 0;
          color: #111827;
          font-size: clamp(34px, 5vw, 58px);
          line-height: 1;
          letter-spacing: -0.065em;
        }

        .section-header p,
        .result-box p {
          margin: 18px 0 0;
          color: #64748b;
          font-size: 17px;
          line-height: 1.75;
          font-weight: 560;
        }

        .features-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 18px;
        }

        .feature-card,
        .audience-card,
        .agent {
          background: rgba(255, 255, 255, 0.78);
          border: 1px solid rgba(148, 163, 184, 0.22);
          box-shadow: 0 24px 70px rgba(15, 23, 42, 0.06);
          transition: 0.22s ease;
        }

        .feature-card {
          padding: 24px;
          border-radius: 30px;
        }

        .feature-card:hover,
        .audience-card:hover,
        .agent:hover {
          transform: translateY(-6px);
          box-shadow: 0 30px 90px rgba(15, 23, 42, 0.1);
        }

        .feature-icon {
          width: 54px;
          height: 54px;
          display: grid;
          place-items: center;
          margin-bottom: 18px;
          border-radius: 20px;
          font-size: 26px;
          background: linear-gradient(135deg, #e0f2fe, #fce7f3, #fef9c3);
        }

        .feature-card h3,
        .audience-card h3,
        .agent h3 {
          margin: 0 0 10px;
          color: #111827;
          font-size: 21px;
          letter-spacing: -0.035em;
        }

        .feature-card p,
        .audience-card p,
        .agent p {
          margin: 0;
          color: #475569;
          line-height: 1.75;
          font-weight: 650;
          font-size: 15.5px;
        }

        .workflow-section,
        .agents-section,
        .results-section {
          width: min(1180px, calc(100% - 32px));
          margin: 0 auto;
          padding: 58px 0;
        }

        .workflow-card,
        .agents-card,
        .result-box {
          border-radius: 42px;
          border: 1px solid rgba(148, 163, 184, 0.22);
          box-shadow: 0 32px 100px rgba(15, 23, 42, 0.08);
        }

        .workflow-card {
          display: grid;
          grid-template-columns: 0.9fr 1.1fr;
          gap: 42px;
          padding: 42px;
          background:
            radial-gradient(circle at top left, rgba(56, 189, 248, 0.22), transparent 34%),
            radial-gradient(circle at bottom right, rgba(251, 113, 133, 0.2), transparent 34%),
            rgba(255, 255, 255, 0.72);
        }

        .timeline {
          display: grid;
          gap: 14px;
        }

        .step {
          display: grid;
          grid-template-columns: 66px 1fr;
          gap: 16px;
          padding: 18px;
          border-radius: 26px;
          background: rgba(255, 255, 255, 0.84);
          border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .step-number {
          width: 54px;
          height: 54px;
          display: grid;
          place-items: center;
          border-radius: 19px;
          color: white;
          background: #111827;
          font-weight: 950;
        }

        .step h3 {
          margin: 0 0 6px;
          color: #111827;
          font-size: 19px;
        }

        .step p {
          margin: 0;
          color: #64748b;
          line-height: 1.65;
          font-weight: 560;
        }

        .audience-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 18px;
        }

        .audience-card {
          padding: 24px;
          border-radius: 30px;
          background:
            radial-gradient(circle at top right, rgba(125, 211, 252, 0.2), transparent 34%),
            rgba(255, 255, 255, 0.78);
        }

        .agents-card {
          display: grid;
          grid-template-columns: 0.85fr 1.15fr;
          gap: 36px;
          padding: 42px;
          background:
            radial-gradient(circle at top left, rgba(253, 224, 71, 0.25), transparent 32%),
            radial-gradient(circle at bottom right, rgba(168, 85, 247, 0.18), transparent 30%),
            rgba(255, 255, 255, 0.74);
        }

        .agents-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        .agent {
          position: relative;
          overflow: hidden;
          min-height: 130px;
          padding: 22px;
          border-radius: 28px;
        }

        .agent::after {
          content: '';
          position: absolute;
          width: 96px;
          height: 96px;
          right: -30px;
          bottom: -30px;
          border-radius: 50%;
          opacity: 0.45;
        }

        .agent.blue::after {
          background: #38bdf8;
        }

        .agent.yellow::after {
          background: #fde047;
        }

        .agent.pink::after {
          background: #fb7185;
        }

        .agent.violet::after {
          background: #a855f7;
        }

        .agent.red::after {
          background: #f97316;
        }

        .agent h3,
        .agent p {
          position: relative;
          z-index: 2;
        }

        .result-box {
          text-align: center;
          padding: 58px 28px;
          background:
            radial-gradient(circle at top left, rgba(253, 224, 71, 0.36), transparent 32%),
            radial-gradient(circle at top right, rgba(56, 189, 248, 0.36), transparent 34%),
            linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(255, 241, 242, 0.82));
        }

        .result-box > span {
          display: inline-flex;
          margin-bottom: 14px;
          padding: 9px 15px;
          border-radius: 999px;
          color: #db2777;
          background: rgba(251, 113, 133, 0.12);
          font-weight: 950;
        }

        .result-box p {
          max-width: 840px;
          margin-left: auto;
          margin-right: auto;
          margin-bottom: 28px;
          color: #475569;
          font-weight: 650;
        }

        .footer {
          width: min(1180px, calc(100% - 32px));
          margin: 0 auto;
          padding: 30px 0 42px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          border-top: 1px solid rgba(148, 163, 184, 0.22);
          color: #64748b;
        }

        .footer p {
          margin: 0;
          font-weight: 650;
        }

        .footer-brand {
          font-size: 20px;
        }

        @media (max-width: 1100px) {
          .features-grid,
          .audience-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .hero,
          .workflow-card,
          .agents-card {
            grid-template-columns: 1fr;
          }

          .hero-dashboard {
            transform: none;
          }
        }

        @media (max-width: 760px) {
          .navbar {
            align-items: flex-start;
            flex-direction: column;
          }

          .nav-links {
            width: 100%;
            flex-wrap: wrap;
            justify-content: center;
            border-radius: 24px;
          }

          .hero {
            padding-top: 30px;
          }

          .features-grid,
          .audience-grid,
          .agents-grid,
          .metrics-grid {
            grid-template-columns: 1fr;
          }

          .workflow-card,
          .agents-card {
            padding: 24px;
          }

          .step {
            grid-template-columns: 1fr;
          }

          .project-preview,
          .export-row,
          .confidence-row {
            align-items: flex-start;
            flex-direction: column;
          }

          .footer {
            align-items: flex-start;
            flex-direction: column;
          }
        }
      `}</style>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReportItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="report-item">
      <div>
        <span className="report-check">✓</span>
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
    </div>
  );
}

function Step({
  number,
  title,
  text,
}: {
  number: string;
  title: string;
  text: string;
}) {
  return (
    <div className="step">
      <div className="step-number">{number}</div>
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </div>
  );
}

function Agent({
  name,
  detail,
  color,
}: {
  name: string;
  detail: string;
  color: AgentColor;
}) {
  return (
    <div className={`agent ${color}`}>
      <h3>{name}</h3>
      <p>{detail}</p>
    </div>
  );
}