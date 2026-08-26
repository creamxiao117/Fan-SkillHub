param(
    [string[]]$ProjectRoots = @(),

    [string]$OutputPath = "",

    [string]$ProjectListFile = "",

    [switch]$IncludeProjectSpecific,

    [double]$SimilarityThreshold = 0.35
)

$ErrorActionPreference = "Stop"

function Get-FirstHeading {
    param([string]$Path)

    $heading = Select-String -LiteralPath $Path -Pattern '^#\s+(.+)$' -Encoding UTF8 -List -ErrorAction SilentlyContinue
    if ($heading) {
        return $heading.Matches[0].Groups[1].Value.Trim()
    }

    return [System.IO.Path]::GetFileNameWithoutExtension($Path)
}

function Remove-FrontMatter {
    param([string]$Text)

    if ($Text -match '(?s)^\s*---\s*.*?\s*---\s*') {
        return ($Text -replace '(?s)^\s*---\s*.*?\s*---\s*', '')
    }

    return $Text
}

function Normalize-Key {
    param([string]$Text)

    return ($Text.ToLowerInvariant() -replace '[^\p{L}\p{N}]+', ' ').Trim()
}

function Get-PlainTextLines {
    param([string]$Text)

    return $Text -split "`r?`n" |
        Where-Object { $_ -notmatch '^\s*```' } |
        ForEach-Object { ($_ -replace '[#>*_\-\[\]()`]', ' ').Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Where-Object { $_ -notmatch '^[A-Za-z_-]+:\s*' }
}

function Get-ShortSummary {
    param(
        [string]$Text,
        [string]$Title
    )

    $line = Get-PlainTextLines -Text $Text |
        Where-Object { $_ -notmatch '^#' } |
        Where-Object { $_ -notmatch '^[A-Za-z_-]+:\s*' } |
        Where-Object { $_ -ne $Title } |
        Where-Object { $_.Length -gt 8 } |
        Select-Object -First 1

    if ($line) {
        if ($line.Length -gt 120) {
            return $line.Substring(0, 120)
        }
        return $line
    }

    return ""
}

function Get-SemanticTerms {
    param([string]$Text)

    $stopWords = @(
        "the", "and", "for", "with", "this", "that", "from", "into", "when", "then",
        "project", "methodology", "card", "rule", "workflow", "process", "current"
    )
    $stopSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($word in $stopWords) {
        [void]$stopSet.Add($word)
    }

    $terms = New-Object System.Collections.Generic.HashSet[string]
    $lower = $Text.ToLowerInvariant()

    foreach ($match in [regex]::Matches($lower, '[a-z0-9][a-z0-9_-]{2,}')) {
        $value = $match.Value.Trim()
        if (-not $stopSet.Contains($value)) {
            [void]$terms.Add($value)
        }
    }

    $cjkChars = [regex]::Matches($Text, '[\u4e00-\u9fff]') | ForEach-Object { $_.Value }
    $cjkText = -join $cjkChars
    if ($cjkText.Length -ge 2) {
        for ($i = 0; $i -le $cjkText.Length - 2; $i++) {
            $gram = $cjkText.Substring($i, 2)
            if (-not $stopSet.Contains($gram)) {
                [void]$terms.Add($gram)
            }
        }
    }

    return @($terms)
}

function Get-TermSimilarity {
    param(
        [string[]]$Left,
        [string[]]$Right
    )

    if ($Left.Count -eq 0 -or $Right.Count -eq 0) {
        return 0
    }

    $leftSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($term in $Left) {
        [void]$leftSet.Add($term)
    }

    $rightSet = New-Object System.Collections.Generic.HashSet[string]
    foreach ($term in $Right) {
        [void]$rightSet.Add($term)
    }

    $intersection = 0
    foreach ($term in $leftSet) {
        if ($rightSet.Contains($term)) {
            $intersection++
        }
    }

    $union = $leftSet.Count + $rightSet.Count - $intersection
    if ($union -eq 0) {
        return 0
    }

    return $intersection / $union
}

function Merge-Terms {
    param(
        [string[]]$Left,
        [string[]]$Right
    )

    $set = New-Object System.Collections.Generic.HashSet[string]
    foreach ($term in $Left) {
        [void]$set.Add($term)
    }
    foreach ($term in $Right) {
        [void]$set.Add($term)
    }

    return @($set)
}

function New-SemanticClusters {
    param(
        [object[]]$Cards,
        [double]$Threshold
    )

    $clusters = New-Object System.Collections.Generic.List[object]

    foreach ($card in ($Cards | Sort-Object Title, Project)) {
        $bestCluster = $null
        $bestScore = 0.0

        foreach ($cluster in $clusters) {
            $score = Get-TermSimilarity -Left $card.Terms -Right $cluster.Terms
            if ($score -gt $bestScore) {
                $bestScore = $score
                $bestCluster = $cluster
            }
        }

        if ($bestCluster -and $bestScore -ge $Threshold) {
            [void]$bestCluster.Items.Add($card)
            $bestCluster.Terms = Merge-Terms -Left $bestCluster.Terms -Right $card.Terms
            if ($bestScore -gt $bestCluster.MaxSimilarity) {
                $bestCluster.MaxSimilarity = $bestScore
            }
        } else {
            $items = New-Object System.Collections.Generic.List[object]
            [void]$items.Add($card)
            [void]$clusters.Add([pscustomobject]@{
                Title = $card.Title
                Items = $items
                Terms = $card.Terms
                MaxSimilarity = 1.0
            })
        }
    }

    return $clusters.ToArray()
}

function Test-ContainsAny {
    param(
        [string]$Text,
        [string[]]$Keywords
    )

    foreach ($keyword in $Keywords) {
        if ($Text -match [regex]::Escape($keyword)) {
            return $true
        }
    }

    return $false
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $skillRoot = Split-Path -Parent $scriptRoot
    $OutputPath = Join-Path $skillRoot "skill-feedback-inbox\feedback-candidates.md"
}

$outputDir = Split-Path -Parent $OutputPath

if (-not [string]::IsNullOrWhiteSpace($ProjectListFile)) {
    if (-not (Test-Path -LiteralPath $ProjectListFile)) {
        throw "Project list file not found: $ProjectListFile"
    }

    $listedProjects = Get-Content -Encoding UTF8 -LiteralPath $ProjectListFile |
        ForEach-Object { $_.Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Where-Object { $_ -notmatch '^\s*#' }

    if ($listedProjects.Count -gt 0) {
        $ProjectRoots = @($ProjectRoots + $listedProjects)
    }
}

$ProjectRoots = @(
    $ProjectRoots |
        ForEach-Object { $_.Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Sort-Object -Unique
)

if ($ProjectRoots.Count -eq 0) {
    throw "No project roots supplied. Use -ProjectRoots or -ProjectListFile."
}

$cards = New-Object System.Collections.Generic.List[object]

foreach ($root in $ProjectRoots) {
    $resolvedRoot = Resolve-Path -LiteralPath $root -ErrorAction SilentlyContinue
    if (-not $resolvedRoot) {
        Write-Warning "Project path not found, skipped: $root"
        continue
    }

    $projectRoot = $resolvedRoot.Path
    $projectName = Split-Path -Leaf $projectRoot
    $methodologyRoot = Join-Path $projectRoot "methodology"

    if (-not (Test-Path -LiteralPath $methodologyRoot)) {
        Write-Warning "Methodology directory not found, skipped: $projectRoot"
        continue
    }

    $sharedPath = Join-Path $methodologyRoot "shared-rules-and-experience"
    $projectPath = Join-Path $methodologyRoot "project-specific-rules-and-experience"

    $scanTargets = @()
    if (Test-Path -LiteralPath $sharedPath) {
        $scanTargets += [pscustomobject]@{ Path = $sharedPath; Scope = "cross-project" }
    }
    if ($IncludeProjectSpecific -and (Test-Path -LiteralPath $projectPath)) {
        $scanTargets += [pscustomobject]@{ Path = $projectPath; Scope = "project-only" }
    }

    foreach ($target in $scanTargets) {
        Get-ChildItem -LiteralPath $target.Path -Filter "*.md" -File -Recurse | ForEach-Object {
            $content = Get-Content -Raw -Encoding UTF8 -LiteralPath $_.FullName
            $bodyContent = Remove-FrontMatter -Text $content
            $title = Get-FirstHeading -Path $_.FullName
            $key = Normalize-Key -Text $title
            if ([string]::IsNullOrWhiteSpace($key)) {
                $key = Normalize-Key -Text $_.BaseName
            }
            $semanticText = "$title`n$bodyContent"
            $terms = Get-SemanticTerms -Text $semanticText
            $summary = Get-ShortSummary -Text $bodyContent -Title $title

            $canSimplify = Test-ContainsAny -Text $bodyContent -Keywords @("clarification", "simplify", "reduce", "lighter", "shorter", "cost")
            $preventsSerious = Test-ContainsAny -Text $bodyContent -Keywords @("risk", "failure", "blocker", "drift", "rework", "error")

            $cards.Add([pscustomobject]@{
                Key = $key
                Title = $title
                Project = $projectName
                ProjectRoot = $projectRoot
                Path = $_.FullName
                Scope = $target.Scope
                CanSimplify = $canSimplify
                PreventsSeriousError = $preventsSerious
                Terms = $terms
                Summary = $summary
            })
        }
    }
}

$clusters = New-SemanticClusters -Cards $cards.ToArray() -Threshold $SimilarityThreshold |
    Sort-Object @{ Expression = { $_.Items.Count }; Descending = $true }, Title
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$lines = New-Object System.Collections.Generic.List[string]

$lines.Add("# Skill Feedback Candidates")
$lines.Add("")
$lines.Add("Generated at: $now")
$lines.Add("")
$lines.Add("Scanned projects: $($ProjectRoots.Count)")
$lines.Add("Collected methodology cards: $($cards.Count)")
$lines.Add("Semantic clusters: $($clusters.Count)")
$lines.Add("Similarity threshold: $SimilarityThreshold")
$lines.Add("Project list file: $(if ($ProjectListFile) { $ProjectListFile } else { 'none' })")
$lines.Add("")
$lines.Add("## Recommended Upgrade Candidates")
$lines.Add("")

$recommended = $clusters | Where-Object {
    $items = $_.Items
    $count = $items.Count
    $hasCrossProject = @($items | Where-Object { $_.Scope -eq "cross-project" }).Count -gt 0
    $canSimplify = @($items | Where-Object { $_.CanSimplify }).Count -gt 0
    $preventsSerious = @($items | Where-Object { $_.PreventsSeriousError }).Count -gt 0

    $count -ge 2 -or $hasCrossProject -or $canSimplify -or $preventsSerious
}

if (-not $recommended) {
    $lines.Add("No recommended upgrade candidates.")
    $lines.Add("")
}

foreach ($cluster in $recommended) {
    $items = $cluster.Items
    $first = $items[0]
    $hasCrossProject = @($items | Where-Object { $_.Scope -eq "cross-project" }).Count -gt 0
    $canSimplify = @($items | Where-Object { $_.CanSimplify }).Count -gt 0
    $preventsSerious = @($items | Where-Object { $_.PreventsSeriousError }).Count -gt 0

    $reuseScope = if ($hasCrossProject -or $items.Count -ge 2) { "cross-project" } else { $first.Scope }
    $recommendation = if ($preventsSerious -or $hasCrossProject -or ($items.Count -ge 2 -and $canSimplify)) {
        "update skill"
    } elseif ($items.Count -ge 2) {
        "promote to shared experience"
    } else {
        "do not promote yet"
    }
    $topTerms = @($cluster.Terms | Sort-Object | Select-Object -First 12) -join ", "

    $lines.Add("### $($first.Title)")
    $lines.Add("")
    $lines.Add("- Occurrences: $($items.Count)")
    $lines.Add("- Reuse scope: $reuseScope")
    $lines.Add("- Can simplify workflow: $(if ($canSimplify) { 'yes' } else { 'unknown' })")
    $lines.Add("- Can prevent serious errors: $(if ($preventsSerious) { 'yes' } else { 'unknown' })")
    $lines.Add("- Semantic terms: $topTerms")
    $lines.Add("- Recommendation: $recommendation")
    $lines.Add("")
    if ($first.Summary) {
        $lines.Add("Summary:")
        $lines.Add("")
        $lines.Add("> $($first.Summary)")
        $lines.Add("")
    }
    $lines.Add("Sources:")
    foreach ($item in $items) {
        $relativePath = Resolve-Path -LiteralPath $item.Path
        $lines.Add("- $($item.Project): $relativePath")
    }
    $lines.Add("")
}

$lines.Add("## All Candidates")
$lines.Add("")

if ($cards.Count -eq 0) {
    $lines.Add("No methodology cards collected.")
    $lines.Add("")
} else {
    foreach ($card in ($cards | Sort-Object Project, Title)) {
        $lines.Add("### $($card.Title)")
        $lines.Add("")
        $lines.Add("- Source project: $($card.Project)")
        $lines.Add("- Reuse scope: $($card.Scope)")
        $lines.Add("- Can simplify workflow: $(if ($card.CanSimplify) { 'yes' } else { 'unknown' })")
        $lines.Add("- Can prevent serious errors: $(if ($card.PreventsSeriousError) { 'yes' } else { 'unknown' })")
        $lines.Add("- Semantic terms: $(@($card.Terms | Sort-Object | Select-Object -First 10) -join ', ')")
        if ($card.Summary) {
            $lines.Add("- Summary: $($card.Summary)")
        }
        $lines.Add("- Source file: $($card.Path)")
        $lines.Add("")
    }
}

if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$reviewedPath = Join-Path $outputDir "feedback-candidates.reviewed.md"
if (-not (Test-Path -LiteralPath $reviewedPath)) {
    $reviewedLines = @(
        "# Reviewed Skill Feedback Candidates",
        "",
        "This file records human review results for generated feedback candidates.",
        "",
        "## Reviewed Items",
        ""
    )
    Set-Content -LiteralPath $reviewedPath -Value $reviewedLines -Encoding UTF8
}

Set-Content -LiteralPath $OutputPath -Value $lines -Encoding UTF8
Write-Host "Generated: $OutputPath"
