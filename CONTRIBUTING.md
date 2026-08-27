# Bijdragen aan D-OmniTwin: van issue tot merge

Dit beschrijft hoe een wijziging in D-OmniTwin van melding tot productie gaat. Geen git-commando's, wel de stappen en waarom ze zo lopen.

## Achtergrond

Stappen 2 t/m 7 volgen [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow), het standaardproces van GitHub zelf voor branch-gebaseerd samenwerken. Stap 1 (issue als vertrekpunt) staat niet in die GitHub Flow-documentatie zelf, die begint bij het maken van een branch. [Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/about-issues) zijn in GitHub-documentatie een los proces. De koppeling issue → branch → PR is in de praktijk gangbaar en wordt ondersteund door GitHub's [sluitingskeywords](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests) (`Closes #<nr>`), maar is geen apart gedocumenteerd "flow"-concept. Dit document combineert beide.

## 1. Issue aanmaken

Iemand signaleert een probleem of wenst een feature. Dit wordt vastgelegd als issue: korte titel, beschrijving van wat er moet gebeuren of wat er mis is. Issue krijgt een nummer, bijvoorbeeld #42.

**Doel:** werk staat ergens geregistreerd voordat er code aan wordt besteed. Voorkomt losse afspraken die nergens terug te vinden zijn.

## 2. Branch maken

Wie de issue oppakt, maakt een aparte branch vanaf `main`. Niet direct op `main` werken. Branchnaam: `feature/<issue-nr>-<korte-naam>`.

**Doel:** de wijziging is geïsoleerd. `main` blijft altijd bruikbaar, ook terwijl iemand nog aan het werk is. De branchnaam verwijst naar het issuenummer, zodat duidelijk is welk werk waar hoort.

## 3. Committen

Op de branch wordt de issue uitgewerkt in kleine, afgeronde commits. Elke commit is een logische stap, geen verzamelbak.

**Doel:** wijzigingen zijn te volgen en terug te draaien zonder ander werk mee te slepen.

## 4. Pull request aanmaken

Zodra het werk klaar is (of eerder, als vroege feedback gewenst is), wordt de branch aangeboden als pull request naar `main`. De PR-beschrijving verwijst naar de issue, bijvoorbeeld "Closes #42".

**Doel:** de wijziging wordt expliciet ter beoordeling voorgelegd voordat die in `main` komt. De koppeling met het issue houdt de herkomst van de wijziging traceerbaar.

## 5. Review

Een collega beoordeelt de pull request: werkt het, is de aanpak logisch, ontbreekt er iets. Commentaar kan leiden tot aanvullende commits op dezelfde branch, die automatisch in de PR verschijnen.

**Doel:** een tweede blik voordat iets in `main` terechtkomt. Niemand merget eigen werk zonder akkoord.

## 6. Mergen

Na akkoord wordt de pull request gemerged in `main`. De issue sluit automatisch, dankzij de "Closes #42"-koppeling uit stap 4.

**Doel:** de wijziging is nu onderdeel van de hoofdlijn. Sluiting van de issue is een direct gevolg van de merge, geen aparte handeling.

## 7. Opruimen

De branch wordt verwijderd. De geschiedenis (commits, review, discussie) blijft bewaard via de PR.

**Doel:** geen verouderde branches die verwarring geven over wat nog actueel is.

## Governance-punt: wie mag mergen naar main?

Wie mag mergen naar `main` is een keuze, geen vanzelfsprekendheid. Gangbare opties:
- Verplichte review voordat merge mogelijk is (branch protection)
- Geen self-merge toegestaan
- Minimaal aantal goedkeuringen, afhankelijk van het risico van de wijziging

**Zonder deze afspraken vastgelegd in de repository-instellingen is de procedure vrijblijvend.** Dit besluit (en het inrichten van branch protection op `main`) vereist repository-adminrechten en staat nog open — zie [#29](https://github.com/TLaan/D-OmniTwin/issues/29).

## Werken met GitKraken Desktop

Zelfde proces als hierboven, uitgewerkt met de stappen zoals ze in GitKraken Desktop verlopen. Screenshots zijn verwijzingen naar GitKraken's eigen documentatie (hotlinked, niet gekopieerd), dus ze blijven actueel zolang GitKraken die pagina's onderhoudt.

1. **Issue aanmaken** — klik op het +-icoon in het Issues-paneel links, vul titel en beschrijving in. Synct direct naar GitHub. ([bron](https://help.gitkraken.com/gitkraken-desktop/github-issues/))
2. **Branch maken vanuit de issue** — open de issue, klik op "Create a branch for this issue". Branchnaam wordt automatisch gevuld op basis van de issuetitel, dus de koppeling issue-branch staat meteen vast. ([bron](https://help.gitkraken.com/gitkraken-desktop/github-issues/))
3. **Wijzigingen committen** — werk op de branch. Klik op de WIP-node in de Commit Graph om openstaande wijzigingen te zien, stage ze, en commit met een beschrijvende boodschap. ([bron](https://help.gitkraken.com/gitkraken-desktop/guide/))
4. **Pull request aanmaken** — branch is gepusht. Sleep de branch op het doel (bijvoorbeeld `main`), of gebruik het +-icoon in de Pull Requests-sectie. Titel, beschrijving en issue-koppeling worden hier ingevuld. ([bron](https://help.gitkraken.com/gitkraken-desktop/pull-requests/))
5. **Review** — reviewer opent de PR, klikt op "Review Code and Suggest Changes" voor directe suggesties in de diff-view, of gebruikt "Review on GitKraken.dev" voor de uitgebreidere reviewervaring. ([bron](https://help.gitkraken.com/gitkraken-desktop/pull-requests/))
6. **Mergen** — na goedkeuring: "Merge pull request", kies mergestrategie (merge commit, squash, of rebase). De issue sluit automatisch als de PR-beschrijving "Closes #nummer" bevat, hetzelfde mechanisme als in de GitHub-webinterface. ([bron](https://help.gitkraken.com/gitkraken-desktop/pull-requests/))
7. **Opruimen** — branch verwijderen na merge: rechtsklik de branch in de Commit Graph, kies verwijderen. Geschiedenis blijft bewaard via de PR.

Wie mag mergen is een repository-instelling (branch protection op `main`), niet iets wat GitKraken zelf afdwingt — zie het governance-punt hierboven.

## Bronnen

- [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) (stappen branch t/m opruimen)
- [Issues, algemeen](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/about-issues)
- [Sluitingskeywords (Closes #nummer)](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests)
- [Protected branches / wie mag mergen](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitKraken Desktop, Beginner Guide & Workflow](https://help.gitkraken.com/gitkraken-desktop/guide/)
- [GitKraken Desktop, Pull Requests](https://help.gitkraken.com/gitkraken-desktop/pull-requests/)
- [GitKraken Desktop, GitHub Issues integratie](https://help.gitkraken.com/gitkraken-desktop/github-issues/)
