import {
    BrowserRouter,
    Navigate,
    Route,
    Routes,
    useLocation,
    useNavigate,
} from "react-router-dom";

import {
    Layout,
    NavigationBar,
} from "./components/ui";

import {
    CompanyResearchPage,
    PortfolioResearchPage,
} from "./pages";


/* --------------------------------------------------------------------------
 * Types
 * -------------------------------------------------------------------------- */

type AppPage =
    | "company"
    | "portfolio";


/* --------------------------------------------------------------------------
 * Route Constants
 * -------------------------------------------------------------------------- */

const APP_ROUTES = {
    company: "/company-research",
    portfolio: "/portfolio-research",
} as const;


/* --------------------------------------------------------------------------
 * Route Helpers
 * -------------------------------------------------------------------------- */

function getCurrentPage(
    pathname: string,
): AppPage {
    if (
        pathname.startsWith(
            APP_ROUTES.portfolio,
        )
    ) {
        return "portfolio";
    }

    return "company";
}


/* --------------------------------------------------------------------------
 * Routed Application
 * -------------------------------------------------------------------------- */

function RoutedApp() {
    const location = useLocation();
    const navigate = useNavigate();

    const currentPage = getCurrentPage(
        location.pathname,
    );

    function handleNavigate(
        page: AppPage,
    ): void {
        navigate(APP_ROUTES[page]);
    }

    return (
        <Layout>
            <NavigationBar
                currentPage={currentPage}
                onNavigate={handleNavigate}
            />

            <Routes>
                {/* Default Route */}

                <Route
                    path="/"
                    element={
                        <Navigate
                            to={APP_ROUTES.company}
                            replace
                        />
                    }
                />

                {/* Company Research */}

                <Route
                    path={APP_ROUTES.company}
                    element={
                        <CompanyResearchPage />
                    }
                />

                {/* Portfolio Research */}

                <Route
                    path={APP_ROUTES.portfolio}
                    element={
                        <PortfolioResearchPage />
                    }
                />

                {/* Unknown Route */}

                <Route
                    path="*"
                    element={
                        <Navigate
                            to={APP_ROUTES.company}
                            replace
                        />
                    }
                />
            </Routes>
        </Layout>
    );
}


/* --------------------------------------------------------------------------
 * Application
 * -------------------------------------------------------------------------- */

export default function App() {
    return (
        <BrowserRouter>
            <RoutedApp />
        </BrowserRouter>
    );
}