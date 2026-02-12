export default function PlayStoreListing() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="font-display text-3xl font-bold text-white mb-2">Google Play Store Listing</h1>
      <p className="text-sm text-dark-500 mb-8">Internal reference — not linked from navigation</p>

      <div className="space-y-8 text-dark-300">
        <section className="bg-dark-900 border border-dark-800 rounded-sm p-6">
          <h2 className="font-display text-lg font-semibold text-brand-400 mb-2">App Name</h2>
          <p>SMA Antenna Calculator</p>
        </section>

        <section className="bg-dark-900 border border-dark-800 rounded-sm p-6">
          <h2 className="font-display text-lg font-semibold text-brand-400 mb-2">Short Description (80 chars)</h2>
          <p>Professional Yagi antenna designer & analyzer for ham radio operators. Free!</p>
        </section>

        <section className="bg-dark-900 border border-dark-800 rounded-sm p-6">
          <h2 className="font-display text-lg font-semibold text-brand-400 mb-2">Full Description</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p>SMA Antenna Calculator is a professional-grade Yagi antenna design and analysis tool built for amateur (ham) radio operators, CB enthusiasts, and antenna engineers.</p>
            <p>Design, analyze, and optimize Yagi-Uda antennas across 9 amateur radio bands — from 17 meters to 70 centimeters.</p>
            <p className="font-semibold text-white mt-4">KEY FEATURES:</p>
            <p className="font-semibold text-white">Antenna Design & Analysis</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Full Yagi-Uda antenna modeling with up to 20 elements</li>
              <li>Real-time SWR bandwidth visualization</li>
              <li>Gain, F/B ratio, and impedance calculations</li>
              <li>Radiation pattern plotting (azimuth and elevation)</li>
              <li>Take-off angle analysis for DX optimization</li>
            </ul>
            <p className="font-semibold text-white">Bands Supported</p>
            <ul className="list-disc list-inside space-y-1">
              <li>HF: 17m, 15m, 12m, 10m, 11m CB</li>
              <li>VHF: 6m, 2m, 1.25m</li>
              <li>UHF: 70cm</li>
            </ul>
            <p className="font-semibold text-white">Advanced Features</p>
            <ul className="list-disc list-inside space-y-1">
              <li>3-way boom mount correction (Bonded, Insulated, Non-Conductive)</li>
              <li>Corrected cut list for accurate element fabrication</li>
              <li>Stacking calculations (vertical, horizontal, and 2x2 quad)</li>
              <li>Visual element viewer with top-view layout</li>
              <li>Spec sheet export (CSV format)</li>
            </ul>
            <p>Built by a ham radio operator, for ham radio operators. 73 de SMA!</p>
          </div>
        </section>

        <section className="bg-dark-900 border border-dark-800 rounded-sm p-6">
          <h2 className="font-display text-lg font-semibold text-brand-400 mb-2">Category & Tags</h2>
          <p><strong>Category:</strong> Tools</p>
          <p><strong>Tags:</strong> ham radio, antenna, yagi, amateur radio, SWR, antenna calculator, radio, HF, VHF, UHF, CB radio</p>
          <p><strong>Content Rating:</strong> Everyone</p>
          <p><strong>Contact:</strong> fallstommy@gmail.com</p>
        </section>
      </div>
    </div>
  )
}
