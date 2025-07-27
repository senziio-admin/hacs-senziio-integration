import { LitElement, html } from
  "https://cdn.jsdelivr.net/npm/lit-element@4.1.1/+esm";

window.customCards = window.customCards || [];
window.customCards.push({
  type:        "senziio-data",
  name:        "Senziio Data Card",
  preview:     true,
  description: "Shows Senziio entities"
});

class SenziioDataCard extends LitElement {
  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  static getStubConfig() {
    return { entities: [] };
  }

  setConfig(config) {
    if (!Array.isArray(config.entities) || !config.entities.length) {
      throw new Error("senziio-data: define at least one entity");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this.requestUpdate();
  }

  render() {
    if (!this._hass || !this._config) return html``;

    const items = this._config.entities
      .map(id => this._hass.states[id])
      .filter(Boolean)
      .map(st => html`
        <li>
          <strong>${st.attributes.friendly_name ?? st.entity_id}</strong>:
          ${st.state}
        </li>
      `);

    return html`
      <ha-card header="${this._config.title ?? 'Senziio Sensors'}">
        <ul style="list-style:none;margin:0;padding:8px">
          ${items}
        </ul>
      </ha-card>
    `;
  }

  getCardSize() {
    return this._config?.entities?.length || 1;
  }
}

customElements.define("senziio-data", SenziioDataCard);
