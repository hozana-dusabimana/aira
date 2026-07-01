import { Link } from 'react-router-dom';
import { APK_URL } from '../config';

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-container landing-nav">
          <Link to="/" className="brand">
            <div className="brand-mark">A</div>
            <div className="brand-text">
              <strong>AIRA</strong>
              <span>Rwanda National Police</span>
            </div>
          </Link>
          <nav className="landing-nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#about">About</a>
            <a href="#contact">Contact</a>
          </nav>
          <div className="landing-nav-cta">
            <a href={APK_URL} className="btn-ghost" download>Get the app</a>
            <Link to="/login" className="btn-outline">Officer sign in</Link>
          </div>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-container hero-grid">
          <div className="hero-copy">
            <span className="eyebrow">AI-Powered Accident Reporting Application</span>
            <h1>Smarter road-accident response, powered by AI.</h1>
            <p>
              AIRA helps Rwanda National Police receive, triage and resolve
              citizen-reported road accidents in real time — combining mobile
              reporting, AI verification and a unified operations dashboard.
            </p>
            <div className="hero-actions">
              <a href={APK_URL} className="btn-primary btn-download" download>
                <span aria-hidden="true">⬇</span> Download Android app
              </a>
              <Link to="/login" className="btn-ghost">Sign in to dashboard</Link>
              <a href="#how-it-works" className="btn-ghost">Learn more</a>
            </div>
            <p className="hero-apk-note">Android APK · install from a trusted source enabled</p>
            <div className="hero-stats">
              <div>
                <strong>24/7</strong>
                <span>Real-time reporting</span>
              </div>
              <div>
                <strong>AI</strong>
                <span>Image verification</span>
              </div>
              <div>
                <strong>GIS</strong>
                <span>Map-based dispatch</span>
              </div>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-card">
              <div className="hero-card-row">
                <span className="dot dot-red" />
                <div>
                  <strong>Critical accident</strong>
                  <small>Kicukiro · 2 min ago</small>
                </div>
                <span className="badge-mini critical">Critical</span>
              </div>
              <div className="hero-card-row">
                <span className="dot dot-orange" />
                <div>
                  <strong>Traffic accident</strong>
                  <small>Kigali City · 8 min ago</small>
                </div>
                <span className="badge-mini high">High</span>
              </div>
              <div className="hero-card-row">
                <span className="dot dot-yellow" />
                <div>
                  <strong>Motorcycle accident</strong>
                  <small>Gasabo · 15 min ago</small>
                </div>
                <span className="badge-mini medium">Medium</span>
              </div>
              <div className="hero-card-row">
                <span className="dot dot-green" />
                <div>
                  <strong>Resolved · minor collision</strong>
                  <small>Nyarugenge · 22 min ago</small>
                </div>
                <span className="badge-mini resolved">Resolved</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="landing-section">
        <div className="landing-container">
          <div className="section-head">
            <span className="eyebrow">What AIRA delivers</span>
            <h2>Built for modern policing</h2>
            <p>End-to-end tooling for citizens to report and for officers to respond — quickly, accurately, and accountably.</p>
          </div>
          <div className="feature-grid">
            <div className="feature-card">
              <div className="feature-icon">📱</div>
              <h3>Mobile reporting</h3>
              <p>Citizens report road accidents with photos, GPS location and severity in seconds from any Android device.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>AI verification</h3>
              <p>On-device and server-side ML models verify imagery, classify severity and suppress false reports.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🗺️</div>
              <h3>Live operations map</h3>
              <p>Dispatch officers from a unified map view with real-time accident tracking and unit location.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3>Real-time alerts</h3>
              <p>WebSocket and FCM push notifications keep officers and command informed the moment things change.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Analytics & insights</h3>
              <p>Trends, hotspots and response-time dashboards help leadership make data-driven decisions.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔒</div>
              <h3>Secure by design</h3>
              <p>Role-based access, JWT auth, rate limiting and full audit trails protect every action and record.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="landing-section landing-section-alt">
        <div className="landing-container">
          <div className="section-head">
            <span className="eyebrow">How it works</span>
            <h2>From report to resolution in four steps</h2>
          </div>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">01</div>
              <h3>Citizen reports</h3>
              <p>A citizen captures evidence in the AIRA mobile app and submits a geotagged road accident.</p>
            </div>
            <div className="step-card">
              <div className="step-number">02</div>
              <h3>AI triage</h3>
              <p>Our AI verifies the image, predicts severity and routes the case to the right station.</p>
            </div>
            <div className="step-card">
              <div className="step-number">03</div>
              <h3>Officer dispatch</h3>
              <p>Command assigns an officer from the map, who receives push alerts with full context.</p>
            </div>
            <div className="step-card">
              <div className="step-number">04</div>
              <h3>Resolution & audit</h3>
              <p>Officers update status, communicate with the reporter and close the case with evidence.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="about" className="landing-section">
        <div className="landing-container about-grid">
          <div>
            <span className="eyebrow">About AIRA</span>
            <h2>A safer Rwanda, together.</h2>
            <p>
              AIRA — the AI-Powered Accident Reporting Application — is a joint initiative
              that brings citizens and the Rwanda National Police closer through
              technology. By combining a friendly mobile experience with serious
              operations tooling, AIRA reduces response times and increases trust
              in public-safety services.
            </p>
            <ul className="checklist">
              <li>Built for the realities of community policing</li>
              <li>Designed for low-bandwidth and offline scenarios</li>
              <li>Open architecture, on-prem or cloud deployable</li>
            </ul>
          </div>
          <div className="about-stats">
            <div className="stat-card">
              <strong>&lt; 60s</strong>
              <span>Average report submission</span>
            </div>
            <div className="stat-card">
              <strong>3</strong>
              <span>Apps in one platform</span>
            </div>
            <div className="stat-card">
              <strong>100%</strong>
              <span>Audited actions</span>
            </div>
            <div className="stat-card">
              <strong>Live</strong>
              <span>Real-time sync</span>
            </div>
          </div>
        </div>
      </section>

      <section id="contact" className="landing-cta">
        <div className="landing-container cta-inner">
          <div>
            <h2>Ready to log in?</h2>
            <p>Sign in with your officer credentials to access the operations dashboard.</p>
          </div>
          <Link to="/login" className="btn-primary btn-large">Officer sign in →</Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-container footer-inner">
          <div className="brand">
            <div className="brand-mark">A</div>
            <div className="brand-text">
              <strong>AIRA</strong>
              <span>Rwanda National Police</span>
            </div>
          </div>
          <div className="footer-meta">
            <span>© {new Date().getFullYear()} AIRA · Rwanda National Police</span>
            <span>v1.0.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
