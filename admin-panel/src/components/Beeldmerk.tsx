// Beeldmerk van de installatie (#83). Komt uit hetzelfde bestand als de hoofdapp,
// static/images/beeldmerk.svg, zodat een organisatie het op één plek vervangt.
interface BeeldmerkProps {
    size?: number;
    className?: string;
}

export const BEELDMERK_URL = '/static/images/beeldmerk.svg';

export default function Beeldmerk({ size = 40, className = 'beeldmerk' }: BeeldmerkProps) {
    return (
        <img
            src={BEELDMERK_URL}
            alt="D-OmniTwin"
            className={className}
            style={{ height: size, width: 'auto', maxWidth: size * 4, objectFit: 'contain' }}
        />
    );
}
