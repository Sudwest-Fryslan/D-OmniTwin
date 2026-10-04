// Beeldmerk van de installatie (#83). Komt uit hetzelfde bestand als de hoofdapp,
// static/images/beeldmerk.svg, zodat een organisatie het op één plek vervangt.
//
// Themakleuren (#249, #251): <use href="beeldmerk.svg#beeldmerk"> tekent de groep met id
// "beeldmerk", met de kleuren uit de tokens --d-omnitwin-beeldmerk-* van het thema. Daaronder
// staat het bestand als <image> met zijn vaste kleuren: zolang het SVG die groep (nog) niet
// heeft, blijft dat zichtbaar; heeft het de groep wel, dan tekent <use> er precies overheen.
interface BeeldmerkProps {
    size?: number;
    className?: string;
}

export const BEELDMERK_URL = '/static/images/beeldmerk.svg';

export default function Beeldmerk({ size = 40, className = 'beeldmerk' }: BeeldmerkProps) {
    return (
        <svg
            className={className}
            viewBox="0 0 64 64"
            width={size}
            height={size}
            role="img"
            aria-label="D-OmniTwin"
            style={{ flexShrink: 0 }}
        >
            <image href={BEELDMERK_URL} width="64" height="64" />
            <use href={`${BEELDMERK_URL}#beeldmerk`} />
        </svg>
    );
}
